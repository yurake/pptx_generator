"""LLM text fit クライアントのユニットテスト。"""

from __future__ import annotations

import json
import sys
import types
from types import SimpleNamespace

import pytest

from pptx_generator.pipeline.mapping import llm_fit
from pptx_generator.pipeline.mapping.llm_fit import (
    AnthropicTextFitClient,
    AwsClaudeTextFitClient,
    AzureOpenAITextFitClient,
    MappingTextFitClientConfigurationError,
    MappingTextFitRequest,
    MappingTextFitResponseFormatError,
    MockMappingTextFitClient,
    OpenAITextFitClient,
    _build_user_prompt,
    _fit_mock_body,
    _normalize_body,
    _normalize_optional_text,
    _parse_text_fit_response,
    create_mapping_text_fit_client,
)


def _install_openai_response_stubs(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    responses_module = types.ModuleType("openai.types.responses")

    class ResponseOutputText:
        def __init__(self, text: str) -> None:
            self.text = text

    class ResponseOutputRefusal:
        def __init__(self, refusal: str) -> None:
            self.refusal = refusal

    class ResponseOutputMessage:
        def __init__(self, content: list[object]) -> None:
            self.content = content

    responses_module.ResponseOutputText = ResponseOutputText
    responses_module.ResponseOutputRefusal = ResponseOutputRefusal
    responses_module.ResponseOutputMessage = ResponseOutputMessage
    monkeypatch.setitem(sys.modules, "openai.types.responses", responses_module)
    return responses_module


def test_create_mapping_text_fit_client_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "mock")
    client = create_mapping_text_fit_client()
    assert isinstance(client, MockMappingTextFitClient)


def test_create_mapping_text_fit_client_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "unknown-provider")
    with pytest.raises(MappingTextFitClientConfigurationError):
        create_mapping_text_fit_client()


def test_parse_text_fit_response_and_normalize() -> None:
    raw_text = json.dumps({"body": ["a", "b"], "subtitle": " sub ", "note": None})
    response = _parse_text_fit_response(raw_text, model="mock")
    assert response.body == ["a", "b"]
    assert response.subtitle == "sub"
    assert response.note is None
    assert _normalize_optional_text("  ") is None
    assert _normalize_optional_text(10) == "10"
    assert _normalize_body(" hello ") == ["hello"]


def test_parse_text_fit_response_invalid_json() -> None:
    with pytest.raises(MappingTextFitResponseFormatError):
        _parse_text_fit_response("not-json", model="mock")


def test_fit_mock_body_trimming() -> None:
    assert _fit_mock_body(["a", "b", "c"], 2, None) == ["a", "b..."]
    assert _fit_mock_body(["a", "b", "c"], None, 2) == ["a", "b..."]


def test_openai_text_fit_client_fit(monkeypatch: pytest.MonkeyPatch) -> None:
    responses_module = _install_openai_response_stubs(monkeypatch)

    class DummyResponse:
        def __init__(self) -> None:
            payload = json.dumps({"body": ["x", "y"]})
            self.output = [
                responses_module.ResponseOutputMessage(
                    [responses_module.ResponseOutputText(payload)]
                )
            ]

    class DummyResponses:
        def create(self, **_kwargs):  # type: ignore[no-untyped-def]
            return DummyResponse()

    dummy_client = SimpleNamespace(responses=DummyResponses())
    request = MappingTextFitRequest(
        slide_id="s01",
        layout_id="layout",
        max_lines=2,
        max_chars=None,
        body=["x", "y", "z"],
    )
    client = OpenAITextFitClient(dummy_client, model="gpt", temperature=0.0, max_tokens=10)
    response = client.fit(request)
    assert response.body == ["x", "y"]


def test_openai_text_fit_client_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyOpenAI:
        def __init__(self, api_key=None, base_url=None):  # noqa: D401
            self.api_key = api_key
            self.base_url = base_url

    openai_module = types.ModuleType("openai")
    openai_module.OpenAI = DummyOpenAI
    monkeypatch.setitem(sys.modules, "openai", openai_module)

    dummy_config = SimpleNamespace(
        api_key="key",
        base_url=None,
        model="gpt-test",
        temperature=0.0,
        max_tokens=10,
    )
    monkeypatch.setattr(llm_fit, "load_openai_chat_config", lambda **_kwargs: dummy_config)
    client = OpenAITextFitClient.from_env()
    assert isinstance(client, OpenAITextFitClient)


def test_azure_text_fit_client_fit(monkeypatch: pytest.MonkeyPatch) -> None:
    responses_module = _install_openai_response_stubs(monkeypatch)

    class DummyResponse:
        def __init__(self) -> None:
            payload = json.dumps({"body": ["a"]})
            self.output = [
                responses_module.ResponseOutputMessage(
                    [responses_module.ResponseOutputText(payload)]
                )
            ]

    class DummyResponses:
        def create(self, **_kwargs):  # type: ignore[no-untyped-def]
            return DummyResponse()

    dummy_client = SimpleNamespace(responses=DummyResponses())
    request = MappingTextFitRequest(
        slide_id="s01",
        layout_id=None,
        max_lines=1,
        max_chars=None,
        body=["a", "b"],
    )
    client = AzureOpenAITextFitClient(dummy_client, deployment="dep", temperature=0.0, max_tokens=10)
    response = client.fit(request)
    assert response.body == ["a"]


def test_azure_text_fit_client_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyAzureOpenAI:
        def __init__(self, api_key=None, api_version=None, azure_endpoint=None):  # noqa: D401
            self.api_key = api_key
            self.api_version = api_version
            self.azure_endpoint = azure_endpoint

    openai_module = types.ModuleType("openai")
    openai_module.AzureOpenAI = DummyAzureOpenAI
    monkeypatch.setitem(sys.modules, "openai", openai_module)

    dummy_config = SimpleNamespace(
        api_key="key",
        api_version="2024-02-15-preview",
        endpoint="https://example.openai.azure.com",
        deployment="dep",
        temperature=0.0,
        max_tokens=10,
    )
    monkeypatch.setattr(llm_fit, "load_azure_openai_config", lambda **_kwargs: dummy_config)
    client = AzureOpenAITextFitClient.from_env()
    assert isinstance(client, AzureOpenAITextFitClient)


def test_anthropic_text_fit_client_fit() -> None:
    class DummyResponse:
        def __init__(self) -> None:
            self.content = [SimpleNamespace(type="text", text=json.dumps({"body": ["ok"]}))]

    class DummyMessages:
        def create(self, **_kwargs):  # type: ignore[no-untyped-def]
            return DummyResponse()

    dummy_client = SimpleNamespace(messages=DummyMessages())
    request = MappingTextFitRequest(
        slide_id="s01",
        layout_id=None,
        max_lines=1,
        max_chars=None,
        body=["ok"],
    )
    client = AnthropicTextFitClient(dummy_client, model="claude", max_tokens=10, temperature=0.0)
    response = client.fit(request)
    assert response.body == ["ok"]


def test_anthropic_text_fit_client_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyAnthropic:
        def __init__(self, api_key=None):  # noqa: D401
            self.api_key = api_key

    anthropic_module = types.ModuleType("anthropic")
    anthropic_module.Anthropic = DummyAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", anthropic_module)

    dummy_config = SimpleNamespace(
        api_key="key",
        model="claude",
        max_tokens=10,
        temperature=0.0,
    )
    monkeypatch.setattr(llm_fit, "load_anthropic_config", lambda **_kwargs: dummy_config)
    client = AnthropicTextFitClient.from_env()
    assert isinstance(client, AnthropicTextFitClient)


def test_aws_claude_text_fit_client_fit() -> None:
    class DummyBody:
        def read(self) -> bytes:
            payload = {"content": [{"text": json.dumps({"body": ["aws"]})}]}
            return json.dumps(payload).encode("utf-8")

    class DummyRuntime:
        def invoke_model(self, **_kwargs):  # type: ignore[no-untyped-def]
            return {"body": DummyBody()}

    request = MappingTextFitRequest(
        slide_id="s01",
        layout_id=None,
        max_lines=1,
        max_chars=None,
        body=["aws"],
    )
    client = AwsClaudeTextFitClient(
        DummyRuntime(),
        model_id="model",
        max_tokens=10,
        inference_profile_arn=None,
        temperature=0.0,
    )
    response = client.fit(request)
    assert response.body == ["aws"]


def test_aws_claude_text_fit_client_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummySession:
        def __init__(self, **_kwargs):  # type: ignore[no-untyped-def]
            pass

        def get_credentials(self):  # type: ignore[no-untyped-def]
            return object()

        def client(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
            return object()

    class DummyBoto3:
        Session = DummySession

    class DummyNoCredentialsError(Exception):
        pass

    boto3_module = types.ModuleType("boto3")
    boto3_module.Session = DummySession
    monkeypatch.setitem(sys.modules, "boto3", boto3_module)

    botocore_exc_module = types.ModuleType("botocore.exceptions")
    botocore_exc_module.NoCredentialsError = DummyNoCredentialsError
    monkeypatch.setitem(sys.modules, "botocore.exceptions", botocore_exc_module)

    dummy_config = SimpleNamespace(
        model_id="model",
        max_tokens=10,
        temperature=0.0,
        region=None,
        profile=None,
        inference_profile_arn=None,
    )
    monkeypatch.setattr(llm_fit, "load_aws_claude_config", lambda **_kwargs: dummy_config)
    client = AwsClaudeTextFitClient.from_env()
    assert isinstance(client, AwsClaudeTextFitClient)


def test_aws_claude_text_fit_client_from_env_no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummySession:
        def __init__(self, **_kwargs):  # type: ignore[no-untyped-def]
            pass

        def get_credentials(self):  # type: ignore[no-untyped-def]
            return None

    boto3_module = types.ModuleType("boto3")
    boto3_module.Session = DummySession
    monkeypatch.setitem(sys.modules, "boto3", boto3_module)

    botocore_exc_module = types.ModuleType("botocore.exceptions")
    botocore_exc_module.NoCredentialsError = RuntimeError
    monkeypatch.setitem(sys.modules, "botocore.exceptions", botocore_exc_module)

    dummy_config = SimpleNamespace(
        model_id="model",
        max_tokens=10,
        temperature=0.0,
        region=None,
        profile=None,
        inference_profile_arn=None,
    )
    monkeypatch.setattr(llm_fit, "load_aws_claude_config", lambda **_kwargs: dummy_config)
    with pytest.raises(MappingTextFitClientConfigurationError):
        AwsClaudeTextFitClient.from_env()


def test_build_user_prompt() -> None:
    request = MappingTextFitRequest(
        slide_id="s01",
        layout_id="layout",
        max_lines=2,
        max_chars=10,
        body=["a", "b"],
        subtitle="sub",
        note="note",
    )
    prompt = _build_user_prompt(request)
    assert "max_lines" in prompt
    assert "layout_id" in prompt
