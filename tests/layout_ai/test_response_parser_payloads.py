"""layout_ai.client のレスポンス解析とクライアント挙動を検証するテスト。"""

from __future__ import annotations

import json
import sys
import types
from types import SimpleNamespace

import pytest

from pptx_generator.layout_ai.client import (
    LayoutAIClientExecutionError,
    LayoutAIRequest,
    LayoutAIResponse,
    LayoutAIResponseFormatError,
    OpenAIChatLayoutClient,
    AnthropicClaudeLayoutClient,
    _coerce_tag_candidates,
    _deduplicate_tags,
    _extract_json_object,
    _parse_layout_response,
)
from pptx_generator.layout_ai.policy import LayoutAIPolicy


def test_extract_json_object_with_wrapped_text() -> None:
    payload = '{"recommended":[{"layout_id":"cover","score":0.9}]}'
    text = f"```json\n{payload}\n```"
    result = _extract_json_object(text)
    assert result["recommended"][0]["layout_id"] == "cover"


def test_extract_json_object_raises_on_missing_object() -> None:
    with pytest.raises(json.JSONDecodeError):
        _extract_json_object("no json here")


def test_parse_layout_response_merges_candidates_and_reasons() -> None:
    text = """
    Response:
    {
      "recommended": [
        {"layout_id": "cover", "score": 0.9, "reason": "primary", "tags": ["intro"]},
        {"layout": "agenda", "fit_score": "0.65", "explanation": ["topics"], "classification": ["agenda", "summary"]}
      ],
      "best_layout": "closing",
      "reasons": {"closing": ["wrap up"]},
      "classifications": {"closing": ["outro"]}
    }
    """
    response = _parse_layout_response(text, model="mock-layout")

    assert isinstance(response, LayoutAIResponse)
    assert [layout for layout, _ in response.recommended] == ["cover", "agenda", "closing"]
    assert response.recommended[0][1] == pytest.approx(0.9)
    assert response.recommended[1][1] == pytest.approx(0.65)
    assert response.reasons["closing"] == "wrap up"
    assert response.classifications["agenda"] == ("agenda", "summary", "topics")
    assert response.classifications["cover"] == ("intro", "primary")
    assert response.classifications["closing"] == ("outro",)


def test_parse_layout_response_without_recommendations() -> None:
    text = '{"reasons":{"layout-x":"details"}}'
    response = _parse_layout_response(text, model="mock-layout")
    assert response.recommended == []


def test_coerce_tag_candidates_various_types() -> None:
    value = {"tags": ["primary", "primary", "secondary"], "label": " extra /text "}
    tags = _coerce_tag_candidates(value)
    assert set(tags) >= {"primary", "secondary", "extra", "text"}

    deduped = _deduplicate_tags(tags)
    expected = tuple(dict.fromkeys(tag.strip().casefold() for tag in tags if tag.strip()))
    assert deduped == expected


def _install_fake_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    module_openai = types.ModuleType("openai")

    class FakeOpenAI:
        def __init__(self, api_key: str, base_url: str | None = None) -> None:
            self.api_key = api_key
            self.base_url = base_url

    module_openai.OpenAI = FakeOpenAI

    class ResponseOutputText:
        def __init__(self, text: str) -> None:
            self.type = "text"
            self.text = text

    class ResponseOutputRefusal:
        def __init__(self, refusal: str) -> None:
            self.type = "refusal"
            self.refusal = refusal

    class ResponseOutputMessage:
        def __init__(self, content, status: str = "complete") -> None:
            self.content = content
            self.status = status

    responses_module = types.ModuleType("openai.types.responses")
    responses_module.ResponseOutputText = ResponseOutputText
    responses_module.ResponseOutputRefusal = ResponseOutputRefusal
    responses_module.ResponseOutputMessage = ResponseOutputMessage

    types_module = types.ModuleType("openai.types")
    types_module.responses = responses_module
    module_openai.types = types.SimpleNamespace(responses=responses_module)

    monkeypatch.setitem(sys.modules, "openai", module_openai)
    monkeypatch.setitem(sys.modules, "openai.types", types_module)
    monkeypatch.setitem(sys.modules, "openai.types.responses", responses_module)


def _make_layout_policy() -> LayoutAIPolicy:
    return LayoutAIPolicy.model_validate(
        {
            "id": "default",
            "name": "Default Policy",
            "prompt_template": "Recommend layout",
        }
    )


def _make_layout_request(policy: LayoutAIPolicy) -> LayoutAIRequest:
    return LayoutAIRequest(
        prompt="Recommend layout",
        policy=policy,
        card_payload={
            "allowed_tags": ["title", "agenda"],
            "allowed_tags_detail": {"title": "メインタイトル"},
        },
        layout_candidates=["cover", "agenda"],
        layout_metadata={
            "agenda": {"usage_tags": ["agenda", "summary"]},
        },
    )


def test_openai_layout_client_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_openai(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "token")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-layout")
    monkeypatch.setenv("OPENAI_TEMPERATURE", "0.2")
    monkeypatch.setenv("OPENAI_MAX_TOKENS", "256")

    client = OpenAIChatLayoutClient.from_env()

    assert isinstance(client, OpenAIChatLayoutClient)


def test_openai_layout_client_recommend_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_openai(monkeypatch)
    payload = json.dumps(
        {
            "recommended": [
                {"layout_id": "cover", "score": 0.92, "reason": "primary", "tags": ["title"]},
                {"layout_id": "agenda", "score": 0.68, "reason": ["topics"], "tags": ["agenda"]},
            ],
            "reasons": {"agenda": "secondary"},
        }
    )

    class ResponseOutputText(sys.modules["openai.types.responses"].ResponseOutputText):  # type: ignore[attr-defined]
        pass

    text = ResponseOutputText(payload)
    message = sys.modules["openai.types.responses"].ResponseOutputMessage([text])  # type: ignore[attr-defined]
    mock_response = SimpleNamespace(output=[message], model="gpt-layout", status="complete")
    client = OpenAIChatLayoutClient(
        SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: mock_response)),
        model="gpt-layout",
        temperature=0.0,
        max_tokens=256,
    )
    policy = _make_layout_policy()
    request = _make_layout_request(policy)

    result = client.recommend(request)

    assert result.recommended[0][0] == "cover"
    assert result.recommended[1][0] == "agenda"
    assert result.reasons["agenda"] == "secondary"


def test_openai_layout_client_recommend_no_recommendations(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_openai(monkeypatch)
    payload = json.dumps({"recommended": []})

    text = sys.modules["openai.types.responses"].ResponseOutputText(payload)  # type: ignore[attr-defined]
    message = sys.modules["openai.types.responses"].ResponseOutputMessage([text])  # type: ignore[attr-defined]
    mock_response = SimpleNamespace(output=[message], model="gpt-layout", status="complete")
    client = OpenAIChatLayoutClient(
        SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: mock_response)),
        model="gpt-layout",
        temperature=0.0,
        max_tokens=256,
    )
    policy = _make_layout_policy()
    request = _make_layout_request(policy)

    with pytest.raises(LayoutAIResponseFormatError):
        client.recommend(request)


def test_openai_layout_client_recommend_api_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_openai(monkeypatch)

    def _raise(**kwargs):
        raise RuntimeError("boom")

    client = OpenAIChatLayoutClient(
        SimpleNamespace(responses=SimpleNamespace(create=_raise)),
        model="gpt-layout",
        temperature=0.0,
        max_tokens=256,
    )
    policy = _make_layout_policy()
    request = _make_layout_request(policy)

    with pytest.raises(LayoutAIClientExecutionError):
        client.recommend(request)


def test_anthropic_layout_client_recommend_success(monkeypatch: pytest.MonkeyPatch) -> None:
    module = types.ModuleType("anthropic")

    class FakeBlock:
        def __init__(self, text: str) -> None:
            self.type = "text"
            self.text = text

    response_holder: dict[str, object] = {}

    class FakeAnthropic:
        def __init__(self, api_key: str) -> None:
            self.messages = SimpleNamespace(create=lambda **kwargs: response_holder["response"])

    module.Anthropic = FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", module)
    monkeypatch.setenv("ANTHROPIC_TEMPERATURE", "0.0")

    payload = json.dumps({"recommended": [{"layout_id": "cover", "score": 0.9}]})
    response_holder["response"] = SimpleNamespace(content=[FakeBlock(payload)], model="claude")

    client = AnthropicClaudeLayoutClient(
        SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: response_holder["response"])),
        model="claude",
        max_tokens=1024,
        temperature=0.0,
    )
    policy = _make_layout_policy()
    request = _make_layout_request(policy)

    result = client.recommend(request)
    assert result.recommended


def test_anthropic_layout_client_recommend_empty_content(monkeypatch: pytest.MonkeyPatch) -> None:
    module = sys.modules.get("anthropic")
    if module is None:
        module = types.ModuleType("anthropic")
        monkeypatch.setitem(sys.modules, "anthropic", module)

    class FakeAnthropic:
        def __init__(self, api_key: str) -> None:
            self.messages = SimpleNamespace(create=lambda **kwargs: SimpleNamespace(content=[], model="claude"))

    module.Anthropic = FakeAnthropic
    client = AnthropicClaudeLayoutClient(
        module.Anthropic("key"),
        model="claude",
        max_tokens=1024,
        temperature=0.0,
    )
    policy = _make_layout_policy()
    request = _make_layout_request(policy)

    with pytest.raises(LayoutAIResponseFormatError):
        client.recommend(request)
