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
        max_tokens = 128
        temperature = 0.0
        region = "us-east-1"
        profile = None
        inference_profile_arn = None

    monkeypatch.setattr(edit_ai_client, "load_aws_claude_config", lambda **kwargs: DummyConfig())

    class DummyRuntimeClient:
        def invoke_model(self, **kwargs):
            return {"body": b'{"content":[{"text":"[]"}]}'}

    class DummySession:
        def __init__(self, **kwargs):
            self._kwargs = kwargs

        def get_credentials(self):
            return object()

        def client(self, service_name: str, **kwargs):
            return DummyRuntimeClient()

    monkeypatch.setitem(sys.modules, "boto3", types.SimpleNamespace(Session=DummySession))
    monkeypatch.setitem(sys.modules, "botocore.exceptions", types.SimpleNamespace(NoCredentialsError=RuntimeError))

    client = edit_ai_client.create_edit_ai_client()
    assert isinstance(client, edit_ai_client.AwsClaudeEditClient)


def test_parse_edits_accepts_edits_wrapper():
    raw = '{"edits": [{"shape_id": 1, "contents": "x", "edit": false, "fit": true}, {"shape_id": 2, "contents": "y"}]}'
    parsed = edit_ai_client._parse_edits(raw)
    assert parsed == [
        {"shape_id": 1, "edit": False, "contents": "x", "fit": True},
        {"shape_id": 2, "edit": True, "contents": "y"},
    ]


def test_parse_edits_accepts_code_fence():
    raw = "```json\n[{\"shape_id\": 1, \"contents\": \"x\"}]\n```"
    parsed = edit_ai_client._parse_edits(raw)
    assert parsed == [{"shape_id": 1, "edit": True, "contents": "x"}]


def test_parse_edits_invalid_json_raises():
    with pytest.raises(edit_ai_client.EditAIResponseFormatError):
        edit_ai_client._parse_edits("not-json")


def test_create_edit_ai_client_unknown_provider(monkeypatch):
    monkeypatch.setattr(
        edit_ai_client, "resolve_llm_provider", lambda: edit_ai_client.ProviderResolution("unknown", "test", None)
    )
    with pytest.raises(edit_ai_client.EditAIClientConfigurationError):
        edit_ai_client.create_edit_ai_client()
