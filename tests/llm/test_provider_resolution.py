from __future__ import annotations

import pytest

from pptx_generator.llm import ProviderResolution, resolve_llm_provider


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
