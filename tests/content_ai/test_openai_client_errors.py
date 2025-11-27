"""OpenAIChatClient のエラー経路を検証するテスト。"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from pptx_generator.content_ai.client import (AIGenerationRequest,
                                              OpenAIChatClient, SlideMatchCandidate,
                                              SlideMatchRequest)
from pptx_generator.content_ai.policy import ContentAIPolicy
from pptx_generator.models import JobAuth, JobMeta, JobSpec, Slide


class _FailingCompletions:
    def create(self, **kwargs):
        raise RuntimeError("synthetic api failure")


def _build_policy() -> ContentAIPolicy:
    return ContentAIPolicy.model_validate(
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
    with caplog.at_level(logging.ERROR, logger="pptx_generator.content_ai.llm"):
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
    with caplog.at_level(logging.ERROR, logger="pptx_generator.content_ai.llm"):
        with pytest.raises(RuntimeError) as excinfo:
            client.match_slide(match_request)

    assert "OpenAI API match call failed" in str(excinfo.value)
    assert any("OpenAI chat completion error" in record.getMessage() for record in caplog.records)
