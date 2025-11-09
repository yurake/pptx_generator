"""Draft structuring pipeline step tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pptx_generator.pipeline import (BriefNormalizationOptions,
                                      BriefNormalizationStep,
                                      DraftStructuringError,
                                      DraftStructuringOptions,
                                      DraftStructuringStep)
from pptx_generator.pipeline.base import PipelineContext
from pptx_generator.pipeline.draft_structuring import SlideIdAligner
from pptx_generator.pipeline.slide_alignment import (SlideAlignmentRecord,
                                                     SlideAlignmentResult)
from pptx_generator.models import JobSpec


@pytest.fixture()
def sample_spec() -> JobSpec:
    payload = {
        "meta": {
            "schema_version": "1.1",
            "title": "Brief Sample Spec",
            "client": "Internal QA",
            "author": "テスト自動化チーム",
            "created_at": "2025-11-02",
            "theme": "standard",
            "locale": "ja-JP",
        },
        "auth": {"created_by": "codex"},
        "slides": [
            {"id": "intro", "layout": "Title", "title": "イントロダクション"},
            {"id": "solution", "layout": "Content", "title": "解決策"},
            {"id": "impact", "layout": "Content", "title": "期待効果"},
            {"id": "next", "layout": "Content", "title": "次のアクション"},
        ],
    }
    return JobSpec.model_validate(payload)


@pytest.fixture()
def brief_paths() -> dict[str, Path]:
    brief_dir = Path("samples/prepare")
    return {
        "cards": brief_dir / "prepare_card.json",
        "log": brief_dir / "brief_log.json",
        "meta": brief_dir / "ai_generation_meta.json",
    }


def test_draft_structuring_generates_documents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sample_spec: JobSpec,
    brief_paths: dict[str, Path],
) -> None:
    monkeypatch.setenv("DRAFT_STORE_DIR", str(tmp_path / "store"))

    def fake_align(
        self: SlideIdAligner,
        *,
        spec: JobSpec,
        brief_document,
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

    brief_step = BriefNormalizationStep(
        BriefNormalizationOptions(
            cards_path=brief_paths["cards"],
            log_path=brief_paths["log"],
            ai_meta_path=brief_paths["meta"],
            require_document=True,
        )
    )
    brief_step.run(context)

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


def test_draft_structuring_fails_when_slide_id_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sample_spec: JobSpec,
    brief_paths: dict[str, Path],
) -> None:
    monkeypatch.setenv("DRAFT_STORE_DIR", str(tmp_path / "store"))

    def fake_align_failure(
        self: SlideIdAligner,
        *,
        spec: JobSpec,
        brief_document,
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

    brief_step = BriefNormalizationStep(
        BriefNormalizationOptions(
            cards_path=brief_paths["cards"],
            log_path=brief_paths["log"],
            ai_meta_path=brief_paths["meta"],
            require_document=True,
        )
    )
    brief_step.run(context)

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
