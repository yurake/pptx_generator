"""AI オーケストレーターのテスト。"""

from __future__ import annotations

from pathlib import Path

import logging

import pytest

from pptx_generator.content_ai import ContentAIOrchestrationError, ContentAIOrchestrator, load_policy_set
from pptx_generator.content_ai.client import AIGenerationResponse
from pptx_generator.models import JobAuth, JobMeta, JobSpec, Slide, SlideBullet, SlideBulletGroup


def test_orchestrator_generates_document(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "mock")
    spec = JobSpec.parse_file(Path("samples/json/sample_jobspec.json"))
    policy_set = load_policy_set(Path("config/content_ai_policies.json"))
    orchestrator = ContentAIOrchestrator(policy_set)

    caplog.set_level(logging.INFO, logger="pptx_generator.content_ai.orchestrator")
    document, meta, logs = orchestrator.generate_document(spec)

    assert len(document.slides) == len(spec.slides)
    assert meta["policy_id"] == policy_set.default_policy_id
    assert len(meta["slides"]) == len(document.slides)
    assert len(logs) == len(document.slides)

    request_logs = [record for record in caplog.records if "AI Request" in record.getMessage()]
    response_logs = [record for record in caplog.records if "AI Response" in record.getMessage()]
    assert request_logs, "AI Request ログが出力されていること"
    assert response_logs, "AI Response ログが出力されていること"

    for slide in document.slides:
        assert slide.status == "draft"
        assert slide.elements.title
        assert slide.elements.body
        assert len(slide.elements.body) <= 6
        for line in slide.elements.body:
            assert len(line) <= 40

    assert meta["spec"]["title"] in logs[0]["prompt"]


class _NoIntentLLMClient:
    def generate(self, request):
        return AIGenerationResponse(title="title", body=["body"], intent=None, model="mock")

    def match_slide(self, request):  # pragma: no cover - interface compatibility
        raise NotImplementedError


def test_orchestrator_raises_when_intent_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    policy_set = load_policy_set(Path("config/content_ai_policies.json"))
    spec = JobSpec(
        meta=JobMeta(schema_version="1.0", title="テスト資料"),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="s01",
                layout="layout_basic",
                title="概要",
                bullets=[SlideBulletGroup(items=[SlideBullet(id="b1", text="本文", level=0)])],
            )
        ],
    )
    orchestrator = ContentAIOrchestrator(policy_set, llm_client=_NoIntentLLMClient())

    with pytest.raises(ContentAIOrchestrationError):
        orchestrator.generate_document(spec)
