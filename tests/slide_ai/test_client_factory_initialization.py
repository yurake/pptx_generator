from __future__ import annotations

import pytest

from pptx_generator.slide_ai import (
    LLMClientConfigurationError,
    MockLLMClient,
    create_llm_client,
)
from pptx_generator.slide_ai.models import AIGenerationRequest, SlideMatchCandidate, SlideMatchRequest


def test_create_llm_client_default_returns_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PPTX_LLM_PROVIDER", raising=False)
    client = create_llm_client()
    assert isinstance(client, MockLLMClient)


def test_create_llm_client_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "unknown-provider")
    with pytest.raises(LLMClientConfigurationError):
        create_llm_client()


def test_create_llm_client_missing_azure_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "azure-openai")
    # openai の実装を実際に import しないように from_env を差し替える
    monkeypatch.setattr(
        "pptx_generator.slide_ai.clients.azure_openai.AzureOpenAIChatClient.from_env",
        lambda: (_ for _ in ()).throw(LLMClientConfigurationError("missing env")),
    )
    # 必須環境変数を明示的に未設定にする
    for key in ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT"]:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(LLMClientConfigurationError):
        create_llm_client()


def test_import_order_clients_then_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    """clients/__init__ を先に import しても循環せず factory が読み込めることを確認。"""

    monkeypatch.setenv("PPTX_LLM_PROVIDER", "mock")
    # 先に clients を import し、その後 factory を import しても例外が出ないことを確認
    import importlib

    import pptx_generator.slide_ai.clients as clients  # noqa: F401

    factory = importlib.reload(__import__("pptx_generator.slide_ai.factory", fromlist=["create_llm_client"]))
    assert hasattr(factory, "create_llm_client")


def test_create_llm_client_default_mock_behaves(monkeypatch: pytest.MonkeyPatch) -> None:
    """デフォルト解決で MockLLMClient が動作することを軽く確認。"""

    monkeypatch.delenv("PPTX_LLM_PROVIDER", raising=False)

    client = create_llm_client()
    assert isinstance(client, MockLLMClient)

    class _DummySlide:
        id = "s1"
        title = "Title"

        @staticmethod
        def iter_bullet_groups():
            return []

    policy = type("Policy", (), {"id": "p", "name": "policy", "model": "mock-local", "safeguards": {}})()
    spec = type("Spec", (), {"meta": type("Meta", (), {"title": "Spec Title"})()})()
    generation_request = AIGenerationRequest(
        prompt="prompt",
        policy=policy,
        spec=spec,
        slide=_DummySlide(),
        intent="overview",
    )
    generation_response = client.generate(generation_request)
    assert generation_response.body

    match_request = SlideMatchRequest(
        card_id="card-1",
        card_chapter=None,
        card_intent=(),
        card_story_phase=None,
        card_summary="",
        prompt="match",
        system_prompt="system",
        candidates=[SlideMatchCandidate(slide_id="c1")],
    )
    match_response = client.match_slide(match_request)
    assert match_response.model == "mock-local"
