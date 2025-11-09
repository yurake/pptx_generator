from pathlib import Path

import json

from pptx_generator.template_ai import TemplateAIOptions, TemplateAIService


def test_template_ai_service_static_rule(tmp_path):
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
                    {"layout_name_pattern": ".*Title.*", "tags": ["title"]},
                ],
            }
        ],
    }
    policy_path.write_text(json.dumps(policy_payload), encoding="utf-8")

    service = TemplateAIService(TemplateAIOptions(policy_path=policy_path))
    result = service.classify_layout(
        template_id="templates",
        layout_id="title_layout",
        layout_name="Title Slide",
        placeholders=[],
        text_hint={},
        media_hint={},
        heuristic_usage_tags=["content"],
    )

    assert result.success
    assert result.usage_tags == ("title",)
    assert result.source == "static"
