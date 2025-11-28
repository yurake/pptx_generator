"""Tests for prepare_ai.llm_client helpers."""

from __future__ import annotations

import os
import sys
import types

import pytest

from pptx_generator.prepare_ai.llm_client import (
    AzureOpenAIPrepareLLMClient,
    MockPrepareLLMClient,
    OpenAIPrepareLLMClient,
    PrepareLLMConfigurationError,
    create_prepare_llm_client,
)


def test_mock_prepare_llm_client_handles_slots() -> None:
    client = MockPrepareLLMClient()
    payload = """
# 入力
{"slot_specs": [{"slot_id": "headline", "context": "Context"}]}
# 出力
"""
    result = client.generate(payload)
    assert "slots" in result.text
    assert result.model == "mock-local"


def test_mock_prepare_llm_client_handles_chapters() -> None:
    client = MockPrepareLLMClient()
    payload = """
# 入力
{"raw_context": {"content": "- bullet"}}
# 出力
"""
    result = client.generate(payload)
    assert "chapters" in result.text


def test_create_prepare_llm_client_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "unknown")
    with pytest.raises(PrepareLLMConfigurationError):
        create_prepare_llm_client()


def test_openai_prepare_client(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeResponse:
        def __init__(self) -> None:
            self.choices = [
                types.SimpleNamespace(message=types.SimpleNamespace(content='{"chapters": []}'))
            ]
            self.usage = types.SimpleNamespace(prompt_tokens=1, completion_tokens=2, total_tokens=3)

    class _FakeCompletions:
        def create(self, **kwargs):
            return _FakeResponse()

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeOpenAI:
        def __init__(self, api_key: str, base_url: str | None = None) -> None:
            self.chat = _FakeChat()

    fake_module = types.SimpleNamespace(OpenAI=_FakeOpenAI)
    monkeypatch.setitem(sys.modules, "openai", fake_module)
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "token")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    client = create_prepare_llm_client()
    assert isinstance(client, OpenAIPrepareLLMClient)
    result = client.generate("prompt")
    assert result.tokens["total"] == 3

    monkeypatch.delitem(sys.modules, "openai", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_azure_prepare_client(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeAzureResponse:
        def __init__(self) -> None:
            content_entry = types.SimpleNamespace(text='{"chapters": []}')
            output_entry = types.SimpleNamespace(content=[content_entry])
            self.output = [output_entry]
            self.usage = types.SimpleNamespace(prompt_tokens=2, completion_tokens=1, total_tokens=3)
            self.output_text = None

    class _FakeAzureResponses:
        def create(self, **kwargs):
            return _FakeAzureResponse()

    class _FakeAzureOpenAI:
        def __init__(self, api_key: str, api_version: str, azure_endpoint: str) -> None:
            self.responses = _FakeAzureResponses()

    fake_module = types.SimpleNamespace(AzureOpenAI=_FakeAzureOpenAI)
    # When testing Azure path we also need OpenAI symbol present to avoid AttributeError if used elsewhere.
    fake_module.OpenAI = lambda *args, **kwargs: None  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "openai", fake_module)
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "azure-openai")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/openai")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "deployment")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

    client = create_prepare_llm_client()
    assert isinstance(client, AzureOpenAIPrepareLLMClient)
    result = client.generate("prompt")
    assert result.tokens["total"] == 3

    monkeypatch.delitem(sys.modules, "openai", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)
