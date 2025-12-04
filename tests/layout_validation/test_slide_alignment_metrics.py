"""Slide ID アライナーのユニットテスト。"""

from __future__ import annotations

import pytest

from pptx_generator.prepare.models import (
    PrepareBodyBlock,
    PrepareCard,
    PrepareCardContent,
    PrepareCardRole,
    PrepareDocument,
)
from pptx_generator.slide_ai import SlideMatchResponse
from pptx_generator.models import (ContentApprovalDocument, ContentElements,
                                   ContentSlide, JobAuth, JobMeta, JobSpec,
                                   Slide)
from pptx_generator.pipeline.slide_alignment import (SlideIdAligner,
                                                     SlideIdAlignerOptions)


def _build_spec() -> JobSpec:
    return JobSpec(
        meta=JobMeta(
            schema_version="1.0",
            title="サンプル提案",
            client="Example Corp",
        ),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(id="intro-slide", layout="Title", title="イントロダクション"),
            Slide(id="solution-slide", layout="Content", title="解決策の概要"),
            Slide(id="orphan", layout="Content", title="未割当"),
        ],
    )


def _build_prepare_document() -> PrepareDocument:
    return PrepareDocument(
        prepare_id="sample",
        cards=[
            PrepareCard(
                card_id="intro",
                order=1,
                role=PrepareCardRole(story_phase="introduction", intent_tags=["introduction"]),
                content=PrepareCardContent(
                    headline="イントロダクション",
                    body=[PrepareBodyBlock(type="paragraph", text="イントロの詳細")],
                ),
            ),
            PrepareCard(
                card_id="solution",
                order=2,
                role=PrepareCardRole(story_phase="solution", intent_tags=["solution"]),
                content=PrepareCardContent(
                    headline="解決策の要点",
                    body=[PrepareBodyBlock(type="paragraph", text="提案内容")],
                ),
            ),
            PrepareCard(
                card_id="orphan",
                order=3,
                role=PrepareCardRole(story_phase="solution", intent_tags=["solution"]),
                content=PrepareCardContent(
                    headline="孤立スライド",
                    body=[PrepareBodyBlock(type="paragraph", text="孤立カード")],
                ),
            ),
        ],
    )


def _build_content_document() -> ContentApprovalDocument:
    return ContentApprovalDocument(
        slides=[
            ContentSlide(id="intro", intent="introduction", elements=ContentElements(title="イントロ")),
            ContentSlide(id="solution", intent="solution", elements=ContentElements(title="解決策")),
            ContentSlide(id="orphan", intent="solution", elements=ContentElements(title="孤立")),
        ]
    )


def test_slide_id_aligner_applies_matching() -> None:
    spec = _build_spec()
    prepare_doc = _build_prepare_document()
    document = _build_content_document()
    aligner = SlideIdAligner(SlideIdAlignerOptions(confidence_threshold=0.1))

    result = aligner.align(spec=spec, prepare_document=prepare_doc, content_document=document)

    aligned_ids = [slide.id for slide in result.document.slides]
    assert aligned_ids == ["intro-slide", "solution-slide", "orphan"]
    assert result.meta["applied"] == 3


def test_slide_id_aligner_skips_without_prepare() -> None:
    spec = _build_spec()
    document = _build_content_document()
    aligner = SlideIdAligner()

    result = aligner.align(spec=spec, prepare_document=None, content_document=document)

    assert result.document == document
    assert result.meta["status"] == "skipped"


def test_slide_id_aligner_reports_unassigned_spec_slide() -> None:
    spec = _build_spec()
    prepare_doc = _build_prepare_document()
    document = ContentApprovalDocument(
        slides=[
            ContentSlide(id="intro", intent="introduction", elements=ContentElements(title="イントロ")),
            ContentSlide(id="solution", intent="solution", elements=ContentElements(title="解決策")),
        ]
    )
    aligner = SlideIdAligner(SlideIdAlignerOptions(confidence_threshold=0.1))

    result = aligner.align(spec=spec, prepare_document=prepare_doc, content_document=document)

    pending_records = {record.card_id: record for record in result.records if record.status != "applied"}
    assert "orphan" in pending_records
    assert pending_records["orphan"].reason == "jobspec_unassigned"
    assert pending_records["orphan"].status == "skipped"
    assert result.meta["jobspec_total"] == 1
    assert result.meta["jobspec_unassigned"] == 1
    assert result.meta["pending"] == 0


def test_slide_id_aligner_does_not_replace_id_when_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = _build_spec()
    prepare_doc = _build_prepare_document()
    document = ContentApprovalDocument(
        slides=[
            ContentSlide(id="intro", intent="introduction", elements=ContentElements(title="イントロ")),
        ]
    )
    aligner = SlideIdAligner(SlideIdAlignerOptions(confidence_threshold=0.9))

    captured: dict[str, str] = {}

    class DummyClient:
        def match_slide(self, request):
            candidate_id = request.candidates[0].slide_id
            captured["candidate"] = candidate_id
            return SlideMatchResponse(slide_id=candidate_id, confidence=0.1, reason="low confidence")

    monkeypatch.setattr(aligner, "_client", DummyClient())

    result = aligner.align(spec=spec, prepare_document=prepare_doc, content_document=document)

    assert result.document.slides[0].id == captured["candidate"]
    record = next(entry for entry in result.records if entry.card_id == "intro")
    assert record.status == "applied"
    assert record.recommended_slide_id == captured["candidate"]
    assert "low_confidence" in (record.reason or "")


def test_slide_id_aligner_reassigns_to_higher_confidence(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = _build_spec()
    prepare_doc = _build_prepare_document()
    document = ContentApprovalDocument(
        slides=[
            ContentSlide(id="intro", intent="introduction", elements=ContentElements(title="イントロ")),
            ContentSlide(id="solution", intent="solution", elements=ContentElements(title="解決策")),
        ]
    )
    aligner = SlideIdAligner(SlideIdAlignerOptions(confidence_threshold=0.5))

    responses = {
        "intro": SlideMatchResponse(slide_id="solution-slide", confidence=0.4, reason="first"),
        "solution": SlideMatchResponse(slide_id="solution-slide", confidence=0.9, reason="second"),
    }

    class StubClient:
        def match_slide(self, request):
            return responses[request.card_id]

    monkeypatch.setattr(aligner, "_client", StubClient())

    result = aligner.align(spec=spec, prepare_document=prepare_doc, content_document=document)

    records = {record.card_id: record for record in result.records if record.card_id in {"intro", "solution"}}
    assert records["solution"].status == "applied"
    assert records["solution"].recommended_slide_id == "solution-slide"
    assert records["intro"].status == "fallback"
    reason = records["intro"].reason or ""
    assert "reassigned" in reason
    assert "fallback_candidate" in reason
    assert result.meta["fallback"] == 1


def test_slide_id_aligner_rejects_lower_confidence_recommendation(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = _build_spec()
    prepare_doc = _build_prepare_document()
    document = ContentApprovalDocument(
        slides=[
            ContentSlide(id="intro", intent="introduction", elements=ContentElements(title="イントロ")),
            ContentSlide(id="solution", intent="solution", elements=ContentElements(title="解決策")),
        ]
    )
    aligner = SlideIdAligner(SlideIdAlignerOptions(confidence_threshold=0.5))

    responses = {
        "intro": SlideMatchResponse(slide_id="intro-slide", confidence=0.2, reason="first"),
        "solution": SlideMatchResponse(slide_id="intro-slide", confidence=0.1, reason="second"),
    }

    class StubClient:
        def match_slide(self, request):
            return responses[request.card_id]

    monkeypatch.setattr(aligner, "_client", StubClient())

    result = aligner.align(spec=spec, prepare_document=prepare_doc, content_document=document)

    records = {record.card_id: record for record in result.records if record.card_id in {"intro", "solution"}}
    assert records["intro"].status == "applied"
    assert records["intro"].recommended_slide_id == "intro-slide"
    assert "low_confidence" in (records["intro"].reason or "")
    assert records["solution"].status == "fallback"
    assert records["solution"].recommended_slide_id == "solution-slide"
    assert "lower_than_existing" in (records["solution"].reason or "")


def test_slide_id_aligner_applies_fallback_when_response_not_in_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = _build_spec()
    prepare_doc = _build_prepare_document()
    document = ContentApprovalDocument(
        slides=[
            ContentSlide(id="intro", intent="introduction", elements=ContentElements(title="イントロ")),
        ]
    )
    aligner = SlideIdAligner()

    class StubClient:
        def match_slide(self, request):
            return SlideMatchResponse(slide_id="external", confidence=0.7, reason="out-of-range")

    monkeypatch.setattr(aligner, "_client", StubClient())

    result = aligner.align(spec=spec, prepare_document=prepare_doc, content_document=document)

    record = next(entry for entry in result.records if entry.card_id == "intro")
    assert record.status == "fallback"
    assert record.recommended_slide_id == "intro-slide"
    assert "fallback_candidate" in (record.reason or "")
