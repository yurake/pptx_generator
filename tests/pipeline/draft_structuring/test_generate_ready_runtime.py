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
    Slide,
)
from pptx_generator.models.common import TextboxPosition
from pptx_generator.pipeline.draft_structuring.generate_ready_runtime import (
    _build_auto_draw_payload,
    _build_generate_ready_meta,
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


def test_build_auto_draw_payload_handles_empty_and_values() -> None:
    base_slide = Slide(id="s1", layout="Title")
    assert _build_auto_draw_payload(base_slide) == []

    slide_with_boxes = Slide(
        id="s2",
        layout="Title",
        auto_draw_boxes={
            "a1": TextboxPosition(left_in=1.0, top_in=2.0, width_in=3.0, height_in=4.0),
            "a2": TextboxPosition(left_in=0.5, top_in=0.75, width_in=1.25, height_in=1.5),
        },
    )

    payload = _build_auto_draw_payload(slide_with_boxes)
    assert payload == [
        {"anchor": "a1", "left_in": 1.0, "top_in": 2.0, "width_in": 3.0, "height_in": 4.0},
        {"anchor": "a2", "left_in": 0.5, "top_in": 0.75, "width_in": 1.25, "height_in": 1.5},
    ]


def test_build_generate_ready_meta_template_path_fallback(job_spec: JobSpec) -> None:
    draft = DraftDocument(sections=[], meta=DraftMeta(template_id="tpl-fallback"))

    meta = _build_generate_ready_meta(
        draft=draft,
        spec=job_spec,
        template_path=None,
        content_hash="abc123",
    )

    assert meta.template_path == "/tmp/template.pptx"
    assert meta.content_hash == "abc123"
    assert meta.template_version == "tpl-fallback"


def test_build_generate_ready_meta_prefers_argument_over_spec(job_spec: JobSpec) -> None:
    draft = DraftDocument(sections=[], meta=DraftMeta(template_id="tpl-override"))
    override_path = Path("/override/template.pptx")

    meta = _build_generate_ready_meta(
        draft=draft,
        spec=job_spec,
        template_path=override_path,
        content_hash=None,
    )

    assert meta.template_path == str(override_path)
    assert meta.template_version == "tpl-override"


def test_build_generate_ready_meta_keeps_empty_string(job_spec: JobSpec) -> None:
    spec = job_spec.model_copy(deep=True)
    spec.meta.template_path = ""
    draft = DraftDocument(sections=[], meta=DraftMeta(template_id="tpl-empty"))

    meta = _build_generate_ready_meta(
        draft=draft,
        spec=spec,
        template_path=None,
        content_hash=None,
    )

    assert meta.template_path == ""
    assert meta.template_version == "tpl-empty"
