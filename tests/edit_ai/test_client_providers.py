import sys
import types
import pytest

from pptx_generator.edit_ai import client as edit_ai_client


class DummyCompletionChoice:
    def __init__(self, content):
        self.message = types.SimpleNamespace(content=content)


def test_openai_client_execution_error(monkeypatch):
    class DummyCompletions:
        def create(self, **kwargs):
            raise RuntimeError("boom")

    class DummyOpenAI:
        def __init__(self):
            self.chat = types.SimpleNamespace(completions=DummyCompletions())

    monkeypatch.setattr(edit_ai_client, "load_openai_chat_config", lambda **k: types.SimpleNamespace(model="m", max_tokens=10))
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=DummyOpenAI))

    client = edit_ai_client.OpenAIEditClient.from_env()
    with pytest.raises(edit_ai_client.EditAIClientExecutionError):
        client.rewrite(edit_ai_client.EditAIRequest(prompt="p", shape_contexts=[]))


def test_openai_client_parse_error(monkeypatch):
    class DummyCompletions:
        def create(self, **kwargs):
            return types.SimpleNamespace(model="m", choices=[DummyCompletionChoice("not-json")])

    class DummyOpenAI:
        def __init__(self):
            self.chat = types.SimpleNamespace(completions=DummyCompletions())

    monkeypatch.setattr(edit_ai_client, "load_openai_chat_config", lambda **k: types.SimpleNamespace(model="m", max_tokens=10))
    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=DummyOpenAI))

    client = edit_ai_client.OpenAIEditClient.from_env()
    with pytest.raises(edit_ai_client.EditAIResponseFormatError):
        client.rewrite(edit_ai_client.EditAIRequest(prompt="p", shape_contexts=[]))


def test_anthropic_client_execution_error(monkeypatch):
    class DummyMessages:
        def create(self, **kwargs):
            raise RuntimeError("anthropic-boom")

    class DummyAnthropic:
        def __init__(self, **kwargs):
            self.messages = DummyMessages()

    monkeypatch.setattr(edit_ai_client, "load_anthropic_config", lambda **k: types.SimpleNamespace(model="m", max_tokens=10))
    dummy_types = types.SimpleNamespace(MessageParam=dict)
    monkeypatch.setitem(sys.modules, "anthropic.types", dummy_types)
    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace(Anthropic=DummyAnthropic, types=dummy_types))

    client = edit_ai_client.AnthropicEditClient.from_env()
    with pytest.raises(edit_ai_client.EditAIClientExecutionError):
        client.rewrite(edit_ai_client.EditAIRequest(prompt="p", shape_contexts=[]))


def test_anthropic_client_uses_system_top_level(monkeypatch):
    class DummyMessages:
        def __init__(self):
            self.last_kwargs = None

        def create(self, **kwargs):
            self.last_kwargs = kwargs
            return types.SimpleNamespace(
                content=[types.SimpleNamespace(text='[{"shape_id": 1, "contents": "ok"}]')],
                model="m",
            )

    class DummyAnthropic:
        def __init__(self, **kwargs):
            self.messages = DummyMessages()

    monkeypatch.setattr(edit_ai_client, "load_anthropic_config", lambda **k: types.SimpleNamespace(model="m", max_tokens=10))
    dummy_types = types.SimpleNamespace(MessageParam=dict)
    monkeypatch.setitem(sys.modules, "anthropic.types", dummy_types)
    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace(Anthropic=DummyAnthropic, types=dummy_types))

    client = edit_ai_client.AnthropicEditClient.from_env()
    result = client.rewrite(edit_ai_client.EditAIRequest(prompt="p", shape_contexts=[]))

    assert result.edits
    kwargs = client._client.messages.last_kwargs
    assert kwargs["system"] == edit_ai_client.EDIT_SYSTEM_PROMPT
    assert kwargs["messages"] == [{"role": "user", "content": "p"}]


def test_aws_claude_client_execution_error(monkeypatch):
    class DummyRuntimeClient:
        def invoke_model(self, **kwargs):
            raise RuntimeError("aws-boom")

    class DummySession:
        def __init__(self, **kwargs):
            self._kwargs = kwargs

        def get_credentials(self):
            return object()

        def client(self, service_name: str, **kwargs):
            return DummyRuntimeClient()

    monkeypatch.setattr(
        edit_ai_client,
        "load_aws_claude_config",
        lambda **k: types.SimpleNamespace(
            model_id="mid",
            max_tokens=10,
            temperature=0.0,
            region="us-east-1",
            profile=None,
            inference_profile_arn=None,
        ),
    )
    monkeypatch.setitem(sys.modules, "boto3", types.SimpleNamespace(Session=DummySession))
    monkeypatch.setitem(sys.modules, "botocore.exceptions", types.SimpleNamespace(NoCredentialsError=RuntimeError))

    client = edit_ai_client.AwsClaudeEditClient.from_env()
    with pytest.raises(edit_ai_client.EditAIClientExecutionError):
        client.rewrite(edit_ai_client.EditAIRequest(prompt="p", shape_contexts=[]))


def test_parse_edits_invalid_type():
    with pytest.raises(edit_ai_client.EditAIResponseFormatError):
        edit_ai_client._parse_edits("{\"edits\": {\"bad\": 1}}")
