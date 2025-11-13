from types import SimpleNamespace
import sys

import pytest

from pptx_generator.brief.llm_client import AzureOpenAIBriefLLMClient


class DummyResponses:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.called_with: dict[str, object] | None = None

    def create(self, **kwargs):  # noqa: ANN003
        self.called_with = kwargs
        content_entry = SimpleNamespace(text=self.response_text)
        item = SimpleNamespace(content=[content_entry])
        usage = SimpleNamespace(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        return SimpleNamespace(output=[item], usage=usage)


def test_azure_llm_client_uses_input_payload_for_responses_api():
    responses = DummyResponses('{"chapters": []}')
    client = AzureOpenAIBriefLLMClient(
        client=SimpleNamespace(responses=responses),
        deployment="gpt-4o-mini",
        api_version="2024-02-15-preview",
        temperature=0.3,
        max_tokens=128,
    )

    result = client.generate("PROMPT", model_hint=None)

    assert responses.called_with is not None
    assert responses.called_with["model"] == "gpt-4o-mini"
    assert responses.called_with["input"][1]["content"] == "PROMPT"
    assert "response_format" not in responses.called_with
    assert result.text == '{"chapters": []}'


def test_azure_llm_client_from_env_trims_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_endpoint: dict[str, str] = {}

    class DummyClient(SimpleNamespace):
        pass

    dummy_responses = SimpleNamespace(create=lambda **kwargs: SimpleNamespace(output=[], usage=None))

    def fake_azure_openai(**kwargs):
        captured_endpoint["value"] = kwargs["azure_endpoint"]
        return DummyClient(responses=dummy_responses)

    fake_module = SimpleNamespace(AzureOpenAI=lambda **kwargs: fake_azure_openai(**kwargs))
    monkeypatch.setitem(sys.modules, "openai", fake_module)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/openai/responses")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "dummy-key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "dummy-deployment")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

    client = AzureOpenAIBriefLLMClient.from_env()

    assert isinstance(client, AzureOpenAIBriefLLMClient)
    assert captured_endpoint["value"] == "https://example.openai.azure.com"
