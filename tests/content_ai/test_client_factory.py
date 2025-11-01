from __future__ import annotations

import os

import pytest

from pptx_generator.content_ai import (LLMClientConfigurationError,
                                       MockLLMClient, create_llm_client)


def test_create_llm_client_default_returns_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PPTX_LLM_PROVIDER", raising=False)
    client = create_llm_client()
    assert isinstance(client, MockLLMClient)


def test_create_llm_client_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "unknown-provider")
    with pytest.raises(LLMClientConfigurationError):
        create_llm_client()
