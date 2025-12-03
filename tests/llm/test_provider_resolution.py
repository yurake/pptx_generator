from __future__ import annotations

import pytest

from pptx_generator.llm import (
    ProviderResolution,
    resolve_llm_provider,
    load_openai_chat_config,
    load_azure_openai_config,
    load_anthropic_config,
    load_aws_claude_config,
)


def test_resolve_provider_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PPTX_LLM_PROVIDER", raising=False)
    info = resolve_llm_provider()
    assert isinstance(info, ProviderResolution)
    assert info.provider == "mock"
    assert info.source == "default"
    assert info.raw_value is None


def test_resolve_provider_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "Azure")
    info = resolve_llm_provider()
    assert info.provider == "azure-openai"
    assert info.source == "PPTX_LLM_PROVIDER"


def test_resolve_provider_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "Custom")
    info = resolve_llm_provider()
    assert info.provider == "custom"
    assert info.source == "PPTX_LLM_PROVIDER"


def test_resolve_provider_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PPTX_TEMPLATE_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "bedrock")
    info = resolve_llm_provider(
        primary_env="PPTX_TEMPLATE_LLM_PROVIDER",
        fallback_env="PPTX_LLM_PROVIDER",
    )
    assert info.provider == "aws-claude"
    assert info.source == "PPTX_LLM_PROVIDER"


def test_resolve_provider_blank_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "   ")
    info = resolve_llm_provider()
    assert info.provider == "mock"
    assert info.source == "PPTX_LLM_PROVIDER"


def test_load_openai_chat_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "token")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_TEMPERATURE", raising=False)
    monkeypatch.delenv("OPENAI_MAX_TOKENS", raising=False)
    config = load_openai_chat_config(
        default_model="gpt-default",
        default_temperature=0.5,
        default_max_tokens=1234,
        error_cls=RuntimeError,
    )
    assert config.api_key == "token"
    assert config.model == "gpt-default"
    assert config.temperature == 0.5
    assert config.max_tokens == 1234


def test_load_openai_chat_config_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_TEMPERATURE", raising=False)
    with pytest.raises(RuntimeError):
        load_openai_chat_config(
            default_model="gpt",
            default_temperature=0.0,
            default_max_tokens=1,
            error_cls=RuntimeError,
        )


def test_load_azure_openai_config_trims_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/openai")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "deploy")
    monkeypatch.delenv("AZURE_OPENAI_TEMPERATURE", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_MAX_TOKENS", raising=False)
    config = load_azure_openai_config(
        default_temperature=0.0,
        default_max_tokens=10,
        default_api_version="2024-02-15-preview",
        error_cls=RuntimeError,
    )
    assert config.endpoint == "https://example.openai.azure.com"
    assert config.deployment == "deploy"
    assert config.temperature == 0.0
    assert config.max_tokens == 10


def test_load_anthropic_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    monkeypatch.delenv("ANTHROPIC_TEMPERATURE", raising=False)
    monkeypatch.delenv("ANTHROPIC_MAX_TOKENS", raising=False)
    config = load_anthropic_config(
        default_model="claude-default",
        default_temperature=0.2,
        default_max_tokens=50,
        error_cls=RuntimeError,
    )
    assert config.model == "claude-default"
    assert config.temperature == 0.2
    assert config.max_tokens == 50


def test_load_aws_claude_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AWS_CLAUDE_MODEL_ID", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_CLAUDE_TEMPERATURE", raising=False)
    monkeypatch.delenv("AWS_CLAUDE_MAX_TOKENS", raising=False)
    config = load_aws_claude_config(
        default_model_id="anthropic.default",
        default_temperature=0.1,
        default_max_tokens=200,
        error_cls=RuntimeError,
    )
    assert config.model_id == "anthropic.default"
    assert config.temperature == 0.1
    assert config.max_tokens == 200
