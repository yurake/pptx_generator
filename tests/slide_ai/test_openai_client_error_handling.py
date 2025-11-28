"""OpenAIChatClient のエラー経路を検証するテスト。"""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace

import pytest

from pptx_generator.slide_ai.client import (AIGenerationRequest,
                                            OpenAIChatClient, SlideMatchCandidate,
                                            SlideMatchRequest)
from pptx_generator.slide_ai.policy import SlideAIPolicy
from pptx_generator.models import JobAuth, JobMeta, JobSpec, Slide


@pytest.fixture(autouse=True)
def reset_llm_logger():
    logger = logging.getLogger("pptx_generator.slide_ai.llm")
    logger.handlers.clear()
    logger.filters.clear()
    logger.propagate = True
    yield


class _FailingCompletions:
    def create(self, **kwargs):
        raise RuntimeError("synthetic api failure")


def _build_policy() -> SlideAIPolicy:
    return SlideAIPolicy.model_validate(
        {
            "id": "default",
            "name": "Default Policy",
            "prompt_template": "タイトル: {title}",
            "default_intent": "overview",
        }
    )


def _build_spec() -> JobSpec:
    return JobSpec(
        meta=JobMeta(schema_version="1.0", title="自動生成テスト"),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="slide-1",
                layout="layout_basic",
                title="概要",
            )
        ],
    )


def _build_client() -> OpenAIChatClient:
    failing_client = SimpleNamespace(chat=SimpleNamespace(completions=_FailingCompletions()))
    return OpenAIChatClient(
        failing_client,
        model="gpt-5-mini",
        temperature=0.3,
        max_tokens=1024,
    )


class _SuccessfulCompletions:
    def __init__(self, payload: str) -> None:
        self._payload = payload

    def create(self, **kwargs):
        message = SimpleNamespace(content=self._payload, refusal=None)
        choice = SimpleNamespace(message=message, finish_reason="stop")
        return SimpleNamespace(choices=[choice])


def _build_success_client(payload: str) -> OpenAIChatClient:
    client = SimpleNamespace(chat=SimpleNamespace(completions=_SuccessfulCompletions(payload)))
    return OpenAIChatClient(
        client,
        model="gpt-5-mini",
        temperature=0.3,
        max_tokens=512,
    )


def test_openai_chat_client_generate_logs_and_raises(caplog: pytest.LogCaptureFixture) -> None:
    client = _build_client()
    policy = _build_policy()
    spec = _build_spec()
    request = AIGenerationRequest(
        prompt="生成してください",
        policy=policy,
        spec=spec,
        slide=spec.slides[0],
        intent="overview",
    )

    caplog.clear()
    with caplog.at_level(logging.ERROR, logger="pptx_generator.slide_ai.llm"):
        with pytest.raises(RuntimeError) as excinfo:
            client.generate(request)

    assert "OpenAI API call failed" in str(excinfo.value)
    assert any("OpenAI chat completion error" in record.getMessage() for record in caplog.records)


def test_openai_chat_client_match_slide_logs_and_raises(caplog: pytest.LogCaptureFixture) -> None:
    client = _build_client()
    spec = _build_spec()
    match_request = SlideMatchRequest(
        card_id="card-1",
        card_chapter=None,
        card_intent=("overview",),
        card_story_phase="intro",
        card_summary="サマリー",
        prompt="match",
        system_prompt="system",
        candidates=[SlideMatchCandidate(slide_id=spec.slides[0].id)],
    )

    caplog.clear()
    with caplog.at_level(logging.ERROR, logger="pptx_generator.slide_ai.llm"):
        with pytest.raises(RuntimeError) as excinfo:
            client.match_slide(match_request)

    assert "OpenAI API match call failed" in str(excinfo.value)
    assert any("OpenAI chat completion error" in record.getMessage() for record in caplog.records)


def test_openai_chat_client_generate_success() -> None:
    client = _build_success_client(
        json.dumps({"title": "Generated", "body": ["First", "Second"], "intent": "overview"})
    )
    policy = _build_policy()
    spec = _build_spec()
    request = AIGenerationRequest(
        prompt="生成してください",
        policy=policy,
        spec=spec,
        slide=spec.slides[0],
        intent="overview",
    )

    response = client.generate(request)

    assert response.title == "Generated"
    assert response.body == ["First", "Second"]
    assert response.intent == "overview"
    assert not response.warnings


def test_openai_chat_client_match_slide_success() -> None:
    payload = json.dumps({"slide_id": "slide-1", "confidence": 0.7, "reason": "matched"})
    client = _build_success_client(payload)
    match_request = SlideMatchRequest(
        card_id="card-1",
        card_chapter=None,
        card_intent=("overview",),
        card_story_phase="intro",
        card_summary="サマリー",
        prompt="match",
        system_prompt="system",
        candidates=[SlideMatchCandidate(slide_id="slide-1")],
    )

    response = client.match_slide(match_request)

    assert response.slide_id == "slide-1"
    assert response.confidence == pytest.approx(0.7)
    assert response.reason == "matched"
