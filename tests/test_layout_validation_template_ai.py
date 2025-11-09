import json
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
        width_in=4.0,
        height_in=1.0,
        text=name,
        placeholder_type=placeholder_type.upper(),
        is_placeholder=True,
    )


def test_layout_validation_uses_template_ai(tmp_path):
    policy_path = tmp_path / "template_ai_policy.json"
    policy_payload = {
        "version": "1",
        "default_policy_id": "default",
        "policies": [
            {
                "id": "default",
                "name": "static-mock",
                "provider": "mock",
                "prompt_template": "classify layout usage tags",
                "static_rules": [
                    {"layout_name_pattern": ".*Overview.*", "tags": ["overview", "content"]},
                ],
            }
        ],
    }
    policy_path.write_text(json.dumps(policy_payload), encoding="utf-8")

    layout = LayoutInfo(
        name="Overview Slide",
        identifier="overview",
        anchors=[_shape("Title", "title"), _shape("Body", "body")],
    )
    template_spec = TemplateSpec(
        template_path="dummy.pptx",
        extracted_at="2025-11-09T00:00:00Z",
        layouts=[layout],
        warnings=[],
        errors=[],
    )

    dummy_template = tmp_path / "dummy.pptx"
    dummy_template.write_bytes(b"")

    options = LayoutValidationOptions(
        template_path=dummy_template,
        output_dir=tmp_path,
        template_ai_policy_path=policy_path,
    )
    suite = LayoutValidationSuite(options)

    records, warnings, errors = suite._build_layout_records(template_spec, "templates")

    assert not errors
    assert records[0]["usage_tags"] == ["content", "overview"]
    ai_warnings = [entry for entry in warnings if entry["code"].startswith("usage_tag_ai")]
    assert not ai_warnings
