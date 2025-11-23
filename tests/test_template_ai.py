from pathlib import Path

import json

from pptx_generator.template_ai import TemplateAIOptions, TemplateAIService
from pptx_generator.template_ai.client import create_template_ai_client
from pptx_generator.template_ai.policy import TemplateAIPolicy


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
    assert result.usage_tags == ("title", "content")
    assert result.source == "static"


def test_template_ai_static_rule_preserves_non_body_placeholders(tmp_path):
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
                    {"layout_name_pattern": None, "tags": ["content"]},
                ],
            }
        ],
    }
    policy_path.write_text(json.dumps(policy_payload), encoding="utf-8")

    service = TemplateAIService(TemplateAIOptions(policy_path=policy_path))
    result = service.classify_layout(
        template_id="templates",
        layout_id="chart_layout",
        layout_name="Chart",
        placeholders=[{"type": "chart"}],
        text_hint={},
        media_hint={},
        heuristic_usage_tags=["chart"],
    )

    assert result.success
    assert result.usage_tags == ("content", "chart")
    assert result.source == "static"


def test_template_ai_provider_resolves_to_azure(monkeypatch):
    policy = TemplateAIPolicy(
        id="default",
        name="azure",
        provider="azure-openai",
        prompt_template="classify layout usage tags",
    )

    dummy_client = object()

    class DummyAzureClient:
        @classmethod
        def from_env(cls, policy):
            return dummy_client

    monkeypatch.setattr(
        "pptx_generator.template_ai.client.AzureOpenAITemplateAIClient",
        DummyAzureClient,
    )
    monkeypatch.setenv("PPTX_TEMPLATE_LLM_PROVIDER", "azure-openai")

    client, provider = create_template_ai_client(policy)

    assert client is dummy_client
    assert provider == "azure-openai"

    monkeypatch.delenv("PPTX_TEMPLATE_LLM_PROVIDER", raising=False)
