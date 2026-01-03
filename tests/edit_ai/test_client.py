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
