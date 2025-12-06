"""Tests for static draft structuring helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from pptx_generator.models import (
    ContentApprovalDocument,
    JobSpec,
    TemplateBlueprint,
    TemplateBlueprintSlide,
    TemplateBlueprintSlot,
    TemplateSpec,
)
from pptx_generator.pipeline.draft_structuring.static_runtime import build_static_artifacts
from pptx_generator.pipeline.draft_structuring.step import DraftStructuringStep
from pptx_generator.prepare.models import PrepareDocument, PrepareGenerationMeta


def test_build_static_artifacts_applies_blueprint_defaults() -> None:
    step = DraftStructuringStep()
    step._layout_name_lookup = {"StaticLayout": "StaticLayout"}  # type: ignore[attr-defined]

    blueprint = TemplateBlueprint(
        slides=[
            TemplateBlueprintSlide(
                slide_id="slide-001",
                layout="StaticLayout",
                slots=[
                    TemplateBlueprintSlot(
                        slot_id="slot-title",
                        anchor="Title",
                        content_type="text",
                        required=True,
                        default_text=["静的タイトル"],
                    ),
                    TemplateBlueprintSlot(
                        slot_id="slot-table",
                        anchor="Table",
                        content_type="table",
                        required=False,
                        default_payload={
                            "headers": ["指標"],
                            "rows": [["N/A"]],
                        },
                    ),
                ],
            )
        ]
    )
    template_spec = TemplateSpec(
        template_path="templates/static_layout.pptx",
        extracted_at="2025-12-06T00:00:00Z",
        layouts=[],
        layout_mode="static",
        blueprint=blueprint,
    )

    job_spec = JobSpec.model_validate(
        {
            "meta": {
                "schema_version": "1.0",
                "title": "静的テンプレ",
                "template_path": "templates/static_layout.pptx",
            },
            "auth": {"created_by": "tester"},
            "slides": [
                {
                    "id": "slide-001",
                    "layout": "StaticLayout",
                }
            ],
        }
    )

    prepare_document = PrepareDocument(prepare_id="prep-1", cards=[])
    prepare_meta = PrepareGenerationMeta(
        prepare_id="prep-1",
        generated_at=datetime(2025, 12, 6, tzinfo=timezone.utc),
        policy_id="static-policy",
        input_hash="hash",
        cards=[],
        mode="static",
        blueprint_path="extract/template_spec.json",
        blueprint_hash="sha256:deadbeef",
    )

    artifacts = build_static_artifacts(
        step=step,
        spec=job_spec,
        prepare_document=prepare_document,
        content_document=ContentApprovalDocument(slides=[]),
        template_spec=template_spec,
        prepare_meta=prepare_meta,
    )

    slide = artifacts.generate_ready.slides[0]
    assert slide.layout_id == "StaticLayout"
    assert slide.elements["Title"] == ["静的タイトル"]
    assert slide.elements["Table"]["rows"] == [["N/A"]]

    slot_meta = slide.meta.blueprint_slots
    assert slot_meta[0]["default_applied"] is True
    assert slot_meta[1]["default_applied"] is True

    mapping_slide = artifacts.mapping_log["slides"][0]
    assert mapping_slide["layout_description"]["blueprint_slots"][0]["default_applied"] is True
    assert mapping_slide["layout_description"]["blueprint_slots"][1]["default_applied"] is True

    summary = artifacts.slot_summary
    assert summary["required_fulfilled"] == summary["required_total"]
