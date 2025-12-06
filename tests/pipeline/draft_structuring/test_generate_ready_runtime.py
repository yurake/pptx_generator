"""Tests for generate ready runtime helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from pptx_generator.draft_recommender import LayoutProfile
from pptx_generator.models import (
    ContentApprovalDocument,
    ContentElements,
    ContentSlide,
    DraftDocument,
    DraftLayoutCandidate,
    DraftMeta,
    DraftSection,
    DraftSlideCard,
    GenerateReadyDocument,
    JobSpec,
)
from pptx_generator.pipeline.draft_structuring.generate_ready_runtime import (
    build_generate_ready_document,
    build_generate_ready_meta_payload,
)
from pptx_generator.pipeline.draft_structuring.step import DraftStructuringStep


@pytest.fixture()
def job_spec() -> JobSpec:
    payload = {
        "meta": {
            "schema_version": "1.0",
            "title": "Refactor Demo",
            "template_path": "/tmp/template.pptx",
        },
        "auth": {"created_by": "tester"},
        "slides": [
            {"id": "card-1", "layout": "Title", "title": "Spec Title"},
        ],
    }
    return JobSpec.model_validate(payload)


@pytest.fixture()
def sample_step(job_spec: JobSpec) -> DraftStructuringStep:
    step = DraftStructuringStep()
    step._layout_name_lookup = {slide.layout: slide.layout for slide in job_spec.slides}  # type: ignore[attr-defined]
    step._layout_catalog = {  # type: ignore[attr-defined]
        "Title": LayoutProfile(
            layout_id="Title",
            layout_name="Title",
            usage_tags=("title",),
            text_hint={},
            media_hint={},
            placeholders=(),
        )
    }
    return step


def test_build_generate_ready_document_empty_sections(
    job_spec: JobSpec,
    sample_step: DraftStructuringStep,
) -> None:
    draft = DraftDocument(sections=[], meta=DraftMeta(template_id="tpl-001"))

    generate_ready = build_generate_ready_document(
        step=sample_step,
        spec=job_spec,
        draft=draft,
        content_document=None,
        template_path=None,
    )

    assert isinstance(generate_ready, GenerateReadyDocument)
    assert len(generate_ready.slides) == 1
    assert generate_ready.meta.template_version == "tpl-001"
    assert generate_ready.meta.template_path == "/tmp/template.pptx"


def test_build_generate_ready_document_with_cards(
    job_spec: JobSpec,
    sample_step: DraftStructuringStep,
) -> None:
    draft = DraftDocument(
        sections=[
            DraftSection(
                name="Main",
                order=1,
                slides=[
                    DraftSlideCard(
                        ref_id="card-1",
                        order=1,
                        layout_hint="Title",
                        layout_candidates=[DraftLayoutCandidate(layout_id="Title", score=1.0)],
                    )
                ],
            )
        ],
        meta=DraftMeta(template_id="tpl-002"),
    )
    content_document = ContentApprovalDocument(
        slides=[
            ContentSlide(
                id="card-1",
                intent="overview",
                elements=ContentElements(title="Merged Title", body=["detail line"]),
                status="approved",
            )
        ]
    )
    template_path = Path("/data/templates/slide.pptx")

    generate_ready = build_generate_ready_document(
        step=sample_step,
        spec=job_spec,
        draft=draft,
        content_document=content_document,
        template_path=template_path,
    )

    slide = generate_ready.slides[0]
    assert slide.elements["title"] == "Merged Title"
    assert slide.meta.page_no == 1
    assert generate_ready.meta.template_version == "tpl-002"
    assert generate_ready.meta.template_path == str(template_path)

    ai_summary = {"invoked": 1, "used": 0, "simulated": 0}
    generate_ready.meta.slot_summary = {"Title": 1}
    generate_ready.meta.blueprint_path = "/blueprints/default.json"
    generate_ready.meta.blueprint_hash = "sha256:deadbeef"
    generate_ready.meta.layout_mode = "static"

    payload = build_generate_ready_meta_payload(
        draft=draft,
        generate_ready=generate_ready,
        ai_summary=ai_summary,
    )

    assert payload["sections"][0]["slides"] == 1
    assert payload["template"]["template_id"] == "tpl-002"
    assert payload["statistics"]["total_slides"] == 1
    assert payload["slot_summary"] == {"Title": 1}
    assert payload["mode"] == "static"
