from __future__ import annotations

from types import SimpleNamespace

from pptx_generator.slide_ai.clients.mock import MockLLMClient
from pptx_generator.slide_ai.models import AIGenerationRequest, SlideMatchCandidate, SlideMatchRequest


def _dummy_generation_request() -> AIGenerationRequest:
    class _DummySlide:
        id = "s1"
        title = "Title"

        @staticmethod
        def iter_bullet_groups():
            return []

    policy = SimpleNamespace(id="p", name="policy", model="mock-local", safeguards={})
    spec = SimpleNamespace(meta=SimpleNamespace(title="Spec Title"))
    return AIGenerationRequest(prompt="prompt", policy=policy, spec=spec, slide=_DummySlide(), intent="overview")


def _dummy_match_request() -> SlideMatchRequest:
    candidates = [SlideMatchCandidate(slide_id="c1", title="", layout=None, subtitle=None, notes=None)]
    return SlideMatchRequest(
        card_id="card-1",
        card_chapter=None,
        card_intent=(),
        card_story_phase=None,
        card_summary="",
        prompt="match",
        system_prompt="system",
        candidates=candidates,
    )


def test_mock_generate_returns_minimal_content() -> None:
    client = MockLLMClient()
    request = _dummy_generation_request()

    response = client.generate(request)

    assert response.title != ""
    assert response.body  # 正規化済みの本文が返る
    assert response.intent == "overview"


def test_mock_match_returns_none_when_no_signal() -> None:
    client = MockLLMClient()
    request = _dummy_match_request()

    response = client.match_slide(request)

    assert response.slide_id is None
    assert response.confidence == 0.0
