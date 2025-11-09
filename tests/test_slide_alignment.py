"""Slide ID アライナーのユニットテスト。"""

from __future__ import annotations

import pytest

from pptx_generator.brief.models import BriefCard, BriefDocument, BriefStoryInfo
from pptx_generator.content_ai import SlideMatchResponse
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


def _build_brief() -> BriefDocument:
    return BriefDocument(
        brief_id="sample",
        cards=[
            BriefCard(
                card_id="intro",
                chapter="イントロダクション",
                message="現状と課題の共有",
                narrative=["イントロの詳細"],
                supporting_points=[],
                story=BriefStoryInfo(phase="introduction"),
                intent_tags=["introduction"],
            ),
            BriefCard(
                card_id="solution",
                chapter="解決策",
                message="解決策の要点",
                narrative=["提案内容"],
                supporting_points=[],
                story=BriefStoryInfo(phase="solution"),
                intent_tags=["solution"],
            ),
            BriefCard(
                card_id="orphan",
                chapter="解決策",
                message="孤立スライド",
                narrative=["孤立カード"],
                supporting_points=[],
                story=BriefStoryInfo(phase="solution"),
                intent_tags=["solution"],
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
    brief = _build_brief()
    document = _build_content_document()
    aligner = SlideIdAligner(SlideIdAlignerOptions(confidence_threshold=0.1))

    result = aligner.align(spec=spec, brief_document=brief, content_document=document)

    aligned_ids = [slide.id for slide in result.document.slides]
    assert aligned_ids == ["intro-slide", "solution-slide", "orphan"]
    assert result.meta["applied"] == 3


def test_slide_id_aligner_skips_without_brief() -> None:
    spec = _build_spec()
    document = _build_content_document()
    aligner = SlideIdAligner()

    result = aligner.align(spec=spec, brief_document=None, content_document=document)

    assert result.document == document
    assert result.meta["status"] == "skipped"


def test_slide_id_aligner_reports_unassigned_spec_slide() -> None:
    spec = _build_spec()
    brief = _build_brief()
    document = ContentApprovalDocument(
        slides=[
            ContentSlide(id="intro", intent="introduction", elements=ContentElements(title="イントロ")),
            ContentSlide(id="solution", intent="solution", elements=ContentElements(title="解決策")),
        ]
    )
    aligner = SlideIdAligner(SlideIdAlignerOptions(confidence_threshold=0.1))

    result = aligner.align(spec=spec, brief_document=brief, content_document=document)

    pending_records = {record.card_id: record for record in result.records if record.status != "applied"}
    assert "orphan" in pending_records
    assert pending_records["orphan"].reason == "jobspec_unassigned"
    assert pending_records["orphan"].status == "skipped"
    assert result.meta["jobspec_total"] == 1
    assert result.meta["jobspec_unassigned"] == 1
    assert result.meta["pending"] == 0


def test_slide_id_aligner_does_not_replace_id_when_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = _build_spec()
    brief = _build_brief()
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

    result = aligner.align(spec=spec, brief_document=brief, content_document=document)

    assert result.document.slides[0].id == "intro"
    pending = next(record for record in result.records if record.card_id == "intro")
    assert pending.status == "pending"
    assert pending.recommended_slide_id == captured["candidate"]
