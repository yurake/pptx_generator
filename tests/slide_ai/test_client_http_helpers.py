"""HTTP 周りのヘルパー共通化をカバーするテスト。"""

from __future__ import annotations

import json

from pptx_generator.slide_ai.client import (
    AzureOpenAIChatClient,
    AwsClaudeClient,
    OpenAIChatClient,
)


class _FakeMessage:
    def __init__(self, content, *, refusal: str | None = None) -> None:
        self.content = content
        self.refusal = refusal


class _FakeChoice:
    def __init__(self, message, *, finish_reason: str | None = None) -> None:
        self.message = message
        self.finish_reason = finish_reason


class _FakeChatResponse:
    def __init__(self, choices) -> None:
        self.choices = choices


class _FakeCompletions:
    def __init__(self, response) -> None:
        self._response = response

    def create(self, **kwargs):  # noqa: D401
        """模擬的に chat.completions.create を呼び出す。"""
        self.last_kwargs = kwargs
        return self._response


class _FakeChat:
    def __init__(self, response) -> None:
        self.completions = _FakeCompletions(response)


class _FakeOpenAIClient:
    def __init__(self, response) -> None:
        self.chat = _FakeChat(response)


def test_openai_chat_completion_handles_none_content() -> None:
    response = _FakeChatResponse([_FakeChoice(_FakeMessage(None), finish_reason="stop")])
    client = OpenAIChatClient(_FakeOpenAIClient(response), model="base", temperature=0.0, max_tokens=0)

    text, finish_reason, refusal = client._chat_completion(messages=[], model_name="mock-local")

    assert text == ""
    assert finish_reason == "stop"
    assert refusal is None


def test_openai_chat_completion_joins_non_string_parts() -> None:
    response = _FakeChatResponse([_FakeChoice(_FakeMessage(["a", 2]), finish_reason=None)])
    client = OpenAIChatClient(_FakeOpenAIClient(response), model="base", temperature=0.0, max_tokens=0)

    text, finish_reason, refusal = client._chat_completion(messages=[], model_name="base")

    assert text == "a2"
    assert finish_reason is None
    assert refusal is None


def test_azure_run_response_collects_text_and_refusal(monkeypatch) -> None:
    class _StubText:
        def __init__(self, text: str) -> None:
            self.text = text

    class _StubRefusal:
        def __init__(self, refusal: str) -> None:
            self.refusal = refusal

    class _StubMessage:
        def __init__(self, content) -> None:
            self.content = content

    class _StubOutput:
        def __init__(self) -> None:
            self.output = [_StubMessage([_StubText("hello "), _StubRefusal("deny")])]
            self.incomplete_details = type("Incomplete", (), {"reason": "length"})

    class _StubResponses:
        def __init__(self, output) -> None:
            self._output = output

        def create(self, **kwargs):
            self.last_kwargs = kwargs
            return self._output

    import sys
    import types

    monkeypatch.setitem(sys.modules, "openai.types.responses", types.SimpleNamespace(ResponseOutputMessage=_StubMessage))
    monkeypatch.setitem(
        sys.modules,
        "openai.types.responses.response_output_text",
        types.SimpleNamespace(ResponseOutputText=_StubText),
    )
    monkeypatch.setitem(
        sys.modules,
        "openai.types.responses.response_output_refusal",
        types.SimpleNamespace(ResponseOutputRefusal=_StubRefusal),
    )

    stub_output = _StubOutput()
    client = AzureOpenAIChatClient(
        client=type("StubClient", (), {"responses": _StubResponses(stub_output)})(),
        deployment="dep",
        api_version="v",
        temperature=0.0,
        max_tokens=8,
    )

    text, refusal, finish_reason = client._run_response(model_name="mock-local", input_messages=[])

    assert text == "hello"
    assert refusal == "deny"
    assert finish_reason == "length"


def test_bedrock_invoke_reads_body_and_adds_profile() -> None:
    class _Body:
        def __init__(self, payload: str) -> None:
            self._payload = payload

        def read(self):
            return self._payload

    class _RuntimeClient:
        def __init__(self, body) -> None:
            self._body = body
            self.last_kwargs: dict | None = None

        def invoke_model(self, **kwargs):
            self.last_kwargs = kwargs
            return {"body": self._body}

    body = _Body(json.dumps({"content": [{"text": "ok"}]}))
    runtime_client = _RuntimeClient(body)
    client = AwsClaudeClient(
        runtime_client=runtime_client,
        model_id="base-model",
        max_tokens=1,
        inference_profile_arn="arn:profile",
        temperature=0.0,
    )

    resolved_model = client._resolve_model_id("mock-local")
    text = client._invoke_bedrock(model_id=resolved_model, payload={"key": "value"})

    assert runtime_client.last_kwargs and runtime_client.last_kwargs["inferenceProfileArn"] == "arn:profile"
    assert text == "ok"
