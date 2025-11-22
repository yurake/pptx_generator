"""Draft structuring pipeline step tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pptx_generator.pipeline import (PrepareNormalizationOptions,
                                      PrepareNormalizationStep,
                                      DraftStructuringError,
                                      DraftStructuringOptions,
                                      DraftStructuringStep)
from pptx_generator.pipeline.base import PipelineContext
from pptx_generator.pipeline.draft_structuring import SlideIdAligner
from pptx_generator.pipeline.slide_alignment import (SlideAlignmentRecord,
                                                     SlideAlignmentResult)
from pptx_generator.models import JobSpec, Slide
from pptx_generator.prepare import (
    PrepareBodyBlock,
    PrepareCard,
    PrepareCardContent,
    PrepareCardRole,
    PrepareDocument,
    PrepareNoteEntry,
    PrepareStoryContext,
)


@pytest.fixture()
def sample_spec() -> JobSpec:
    payload = {
        "meta": {
            "schema_version": "1.1",
            "title": "Prepare Sample Spec",
            "client": "Internal QA",
            "author": "テスト自動化チーム",
            "created_at": "2025-11-02",
            "theme": "standard",
            "locale": "ja-JP",
        },
        "auth": {"created_by": "codex"},
        "slides": [
            {"id": "introduction-1", "layout": "Title", "title": "イントロダクション"},
            {"id": "problem-2", "layout": "Content", "title": "課題"},
            {"id": "solution-3", "layout": "Content", "title": "解決策"},
            {"id": "impact-4", "layout": "Content", "title": "期待効果"},
        ],
    }
    return JobSpec.model_validate(payload)


@pytest.fixture()
def prepare_paths() -> dict[str, Path]:
    prepare_dir = Path("samples/prepare")
    return {
        "cards": prepare_dir / "prepare_card.json",
        "log": prepare_dir / "prepare_log.json",
        "meta": prepare_dir / "ai_generation_meta.json",
    }


def test_draft_structuring_generates_documents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sample_spec: JobSpec,
    prepare_paths: dict[str, Path],
) -> None:
    monkeypatch.setenv("DRAFT_STORE_DIR", str(tmp_path / "store"))

    def fake_align(
        self: SlideIdAligner,
        *,
        spec: JobSpec,
        prepare_document,
        content_document,
    ) -> SlideAlignmentResult:
        records = [
            SlideAlignmentRecord(
                card_id=slide.id,
                recommended_slide_id=slide.id,
                confidence=1.0,
                reason="mock",
                status="applied",
            )
            for slide in content_document.slides
        ]
        meta = {
            "status": "completed",
            "threshold": 0.5,
            "cards_total": len(content_document.slides),
            "jobspec_total": 0,
            "jobspec_unassigned": 0,
            "applied": len(content_document.slides),
            "fallback": 0,
            "pending": 0,
        }
        return SlideAlignmentResult(document=content_document, records=records, meta=meta)

    monkeypatch.setattr(SlideIdAligner, "align", fake_align)

    layouts_path = tmp_path / "layouts.jsonl"
    layouts_path.write_text(
        '\n'.join(
            [
                json.dumps(
                    {
                        "layout_id": "Title",
                        "usage_tags": ["title"],
                        "text_hint": {"max_lines": 3},
                        "media_hint": {"allow_table": False},
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "layout_id": "Content",
                        "usage_tags": ["content", "problem"],
                        "text_hint": {"max_lines": 6},
                        "media_hint": {"allow_table": True},
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )

    context = PipelineContext(spec=sample_spec, workdir=tmp_path)

    prepare_step = PrepareNormalizationStep(
        PrepareNormalizationOptions(
            cards_path=prepare_paths["cards"],
            log_path=prepare_paths["log"],
            ai_meta_path=prepare_paths["meta"],
            require_document=True,
        )
    )
    prepare_step.run(context)

    step = DraftStructuringStep(
        DraftStructuringOptions(
            layouts_path=layouts_path,
            output_dir=tmp_path,
        )
    )
    step.run(context)

    draft_path = tmp_path / "draft_approved.json"
    assert draft_path.exists()

    payload = json.loads(draft_path.read_text(encoding="utf-8"))
    assert payload["sections"], "sections should not be empty"
    first_section = payload["sections"][0]
    assert first_section["slides"], "slides should not be empty"
    first_slide = first_section["slides"][0]
    assert first_slide["layout_hint"], "layout_hint should be populated"
    assert first_slide["layout_candidates"], "layout_candidates should not be empty"
    assert "layout_score_detail" in first_slide
    detail = first_slide["layout_score_detail"]
    assert "ai_recommendation" in detail
    assert detail["ai_recommendation"] >= 0.0

    assert context.artifacts["draft_document_path"] == str(draft_path)
    assert (tmp_path / "draft_review_log.json").exists()
    mapping_log_path = tmp_path / "draft_mapping_log.json"
    assert mapping_log_path.exists()
    mapping_payload = json.loads(mapping_log_path.read_text(encoding="utf-8"))
    assert mapping_payload and mapping_payload[0]["ai_recommendation_used"] is not None
    ready_meta_path = tmp_path / "generate_ready_meta.json"
    meta_payload = json.loads(ready_meta_path.read_text(encoding="utf-8"))
    assert meta_payload["ai_recommendation"]["used"] >= 0
    assert "content_alignment_meta" in context.artifacts
    alignment_meta = context.artifacts["content_alignment_meta"]
    assert alignment_meta["applied"] >= 1


def test_convert_slide_elements_omits_auto_draw_anchor() -> None:
    slide = Slide(
        id="intro",
        layout="Title",
        title="イントロ",
        auto_draw_anchors=["Num"],
    )

    elements = DraftStructuringStep._convert_slide_elements(slide)

    assert "Num" not in elements


def test_draft_structuring_fails_when_slide_id_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sample_spec: JobSpec,
    prepare_paths: dict[str, Path],
) -> None:
    monkeypatch.setenv("DRAFT_STORE_DIR", str(tmp_path / "store"))

    def fake_align_failure(
        self: SlideIdAligner,
        *,
        spec: JobSpec,
        prepare_document,
        content_document,
    ) -> SlideAlignmentResult:
        records = [
            SlideAlignmentRecord(
                card_id="missing-slide",
                recommended_slide_id=None,
                confidence=0.0,
                reason="jobspec_unassigned",
                status="pending",
            )
        ]
        meta = {
            "status": "completed",
            "threshold": 0.5,
            "cards_total": len(content_document.slides),
            "jobspec_total": 1,
            "jobspec_unassigned": 1,
            "applied": 0,
            "fallback": 0,
            "pending": 1,
        }
        return SlideAlignmentResult(document=content_document, records=records, meta=meta)

    monkeypatch.setattr(SlideIdAligner, "align", fake_align_failure)

    layouts_path = tmp_path / "layouts.jsonl"
    layouts_path.write_text(
        json.dumps(
            {
                "layout_id": "Content",
                "usage_tags": ["content"],
                "text_hint": {"max_lines": 6},
                "media_hint": {"allow_table": True},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    context = PipelineContext(spec=sample_spec, workdir=tmp_path)

    prepare_step = PrepareNormalizationStep(
        PrepareNormalizationOptions(
            cards_path=prepare_paths["cards"],
            log_path=prepare_paths["log"],
            ai_meta_path=prepare_paths["meta"],
            require_document=True,
        )
    )
    prepare_step.run(context)

    step = DraftStructuringStep(
        DraftStructuringOptions(
            layouts_path=layouts_path,
            output_dir=tmp_path,
        )
    )

    with pytest.raises(DraftStructuringError) as exc_info:
        step.run(context)

    assert "Slide alignment" in str(exc_info.value)
    alignment_meta = context.artifacts.get("content_alignment_meta")
    assert alignment_meta is not None
    assert alignment_meta["pending"] >= 1
    assert alignment_meta["jobspec_unassigned"] >= 1


def test_prepare_normalization_preserves_subtitle(tmp_path: Path, sample_spec: JobSpec) -> None:
    card_with_subtitle = PrepareCard(
        card_id="introduction-1",
        order=1,
        role=PrepareCardRole(story_phase="introduction", intent_tags=["overview"]),
        content=PrepareCardContent(
            headline="Kickoff Message",
            subtitle="Executive Summary",
            body=[PrepareBodyBlock(type="paragraph", text="最初のサマリーです。")],
            notes=[PrepareNoteEntry(text="補足メモ")],
        ),
        meta={"source_chapter": {"id": "intro", "title": "イントロダクション"}},
    )
    card_with_chapter_meta = PrepareCard(
        card_id="problem-1",
        order=2,
        role=PrepareCardRole(story_phase="problem", intent_tags=["details"]),
        content=PrepareCardContent(
            headline="顧客課題の整理",
            body=[PrepareBodyBlock(type="paragraph", text="主要課題を列挙します。")],
        ),
        meta={"source_chapter": {"id": "problem", "title": "現状の課題"}},
    )
    document = PrepareDocument(
        prepare_id="todo-content-elements",
        cards=[card_with_subtitle, card_with_chapter_meta],
        story_context=PrepareStoryContext(),
    )
    cards_path = tmp_path / "prepare_card.json"
    cards_path.write_text(
        json.dumps(document.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )

    context = PipelineContext(spec=sample_spec, workdir=tmp_path)
    step = PrepareNormalizationStep(
        PrepareNormalizationOptions(cards_path=cards_path, require_document=True)
    )
    step.run(context)

    content_document = context.artifacts["content_approved"]
    assert content_document.slides[0].elements.subtitle == "Executive Summary"
    assert content_document.slides[1].elements.subtitle == "現状の課題"
