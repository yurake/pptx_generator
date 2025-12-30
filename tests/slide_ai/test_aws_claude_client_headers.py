from __future__ import annotations

import json
from types import SimpleNamespace

from pptx_generator.slide_ai.client import (
    APPLICATION_JSON,
    AIGenerationRequest,
    AwsClaudeClient,
    SlideMatchCandidate,
    SlideMatchRequest,
)


class _StubRuntimeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def invoke_model(self, **kwargs):
        self.calls.append(kwargs)
        return {"body": json.dumps({"content": [{"text": json.dumps({"title": "t", "body": ["b"]})}]})}


def _dummy_generation_request() -> AIGenerationRequest:
    policy = SimpleNamespace(id="policy-id", model=None, safeguards={}, name="policy")
    spec = SimpleNamespace(meta=SimpleNamespace(title="spec-title"))
    slide = SimpleNamespace(id="slide-1", title="slide-title")
    return AIGenerationRequest(
        prompt="prompt",
        policy=policy,
        spec=spec,
        slide=slide,
        intent="draft",
    )


def test_aws_claude_generate_uses_application_json_headers():
    runtime = _StubRuntimeClient()
    client = AwsClaudeClient(runtime, model_id="model", max_tokens=10, inference_profile_arn=None, temperature=0.3)

    client.generate(_dummy_generation_request())

    assert runtime.calls
    call = runtime.calls[0]
    assert call["contentType"] == APPLICATION_JSON
    assert call["accept"] == APPLICATION_JSON


def test_aws_claude_match_slide_uses_application_json_headers():
    runtime = _StubRuntimeClient()
    client = AwsClaudeClient(runtime, model_id="model", max_tokens=10, inference_profile_arn=None, temperature=0.3)

    request = SlideMatchRequest(
        card_id="card-1",
        card_chapter=None,
        card_intent=("a",),
        card_story_phase=None,
        card_summary="summary",
        prompt="prompt",
        system_prompt="system",
        candidates=[SlideMatchCandidate(slide_id="s1")],
        model=None,
    )
    client.match_slide(request)

    assert runtime.calls
    call = runtime.calls[0]
    assert call["contentType"] == APPLICATION_JSON
    assert call["accept"] == APPLICATION_JSON
