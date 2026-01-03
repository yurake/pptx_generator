import types
import sys

import pytest

from pptx_generator.edit_ai import client as edit_ai_client


def test_create_edit_ai_client_aws_claude(monkeypatch):
    # provider を aws-claude に固定
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "aws-claude")
    # ダミー設定を返す
    class DummyConfig:
        model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        model = model_id
        max_tokens = 128
        temperature = 0.0
        region = "us-east-1"
        profile = None
        inference_profile_arn = None
        api_key = "dummy"
        endpoint = "https://bedrock.runtime.aws"

    monkeypatch.setattr(edit_ai_client, "load_aws_claude_config", lambda **kwargs: DummyConfig())

    # anthropic をダミー化して外部呼び出しを避ける
    dummy_module = types.SimpleNamespace()

    class DummyMessages:
        def create(self, **kwargs):
            return types.SimpleNamespace(model="dummy", content=[])

    class DummyAnthropic:
        def __init__(self, **kwargs):
            self.messages = DummyMessages()

    dummy_module.Anthropic = DummyAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", dummy_module)

    client = edit_ai_client.create_edit_ai_client()
    assert isinstance(client, edit_ai_client.AwsClaudeEditClient)


def test_parse_edits_accepts_edits_wrapper():
    raw = '{"edits": [{"shape_id": 1, "contents": "x", "edit": false}, {"shape_id": 2, "contents": "y"}]}'
    parsed = edit_ai_client._parse_edits(raw)
    assert parsed == [
        {"shape_id": 1, "edit": False, "contents": "x"},
        {"shape_id": 2, "edit": True, "contents": "y"},
    ]


def test_parse_edits_invalid_json_raises():
    with pytest.raises(edit_ai_client.EditAIResponseFormatError):
        edit_ai_client._parse_edits("not-json")


def test_create_edit_ai_client_unknown_provider(monkeypatch):
    monkeypatch.setattr(
        edit_ai_client, "resolve_llm_provider", lambda: edit_ai_client.ProviderResolution("unknown", "test", None)
    )
    with pytest.raises(edit_ai_client.EditAIClientConfigurationError):
        edit_ai_client.create_edit_ai_client()
