from pathlib import Path

from pptx_generator.layout_validation.suite import (
    LayoutValidationOptions,
    LayoutValidationSuite,
)
from pptx_generator.models import LayoutInfo, ShapeInfo, TemplateSpec


def _shape(name: str, placeholder_type: str) -> ShapeInfo:
    return ShapeInfo(
        name=name,
        shape_type="text",
        left_in=1.0,
        top_in=1.0,
        width_in=1.0,
        height_in=1.0,
        text=None,
        placeholder_type=placeholder_type.upper(),
        is_placeholder=True,
    )


def _build_suite() -> LayoutValidationSuite:
    options = LayoutValidationOptions(
        template_path=Path("dummy.pptx"),
        output_dir=Path("out"),
    )
    return LayoutValidationSuite(options)


def test_title_and_content_layout_suppresses_title_tag():
    layout = LayoutInfo(
        name="Title and Content",
        identifier="title_and_content",
        anchors=[_shape("Title", "title"), _shape("Body", "body")],
    )

    spec = TemplateSpec(
        template_path="dummy.pptx",
        extracted_at="2025-11-09T00:00:00Z",
        layouts=[layout],
        warnings=[],
        errors=[],
    )

    suite = _build_suite()
    records, warnings, errors = suite._build_layout_records(spec, "templates")

    assert not errors
    assert records[0]["usage_tags"] == ["content"]
    assert not any(warning["code"] == "usage_tag_title_suppressed" for warning in warnings)


def test_pure_title_layout_retains_title_tag():
    layout = LayoutInfo(
        name="Title Slide",
        identifier="title_slide",
        anchors=[_shape("Title", "title"), _shape("Subtitle", "subtitle")],
    )

    spec = TemplateSpec(
        template_path="dummy.pptx",
        extracted_at="2025-11-09T00:00:00Z",
        layouts=[layout],
        warnings=[],
        errors=[],
    )

    suite = _build_suite()
    records, warnings, errors = suite._build_layout_records(spec, "templates")

    assert not errors
    assert warnings == []
    assert records[0]["usage_tags"] == ["title"]
