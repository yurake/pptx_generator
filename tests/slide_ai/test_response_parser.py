from __future__ import annotations

from types import SimpleNamespace

from pptx_generator.slide_ai.models import AIGenerationRequest, SlideMatchRequest, SlideMatchCandidate
from pptx_generator.slide_ai.response_parser import (
    MAX_BODY_LINE_LENGTH,
    MAX_BODY_LINES,
    _normalize_body,
    build_generation_response,
    build_slide_match_response,
)


def _dummy_request() -> AIGenerationRequest:
    policy = SimpleNamespace(id="p", name="policy", model="mock-local", safeguards={})
    spec = SimpleNamespace(meta=SimpleNamespace(title="Spec Title"))
    slide = SimpleNamespace(id="s1", title="Slide Title")
    return AIGenerationRequest(prompt="prompt", policy=policy, spec=spec, slide=slide, intent="overview")


def test_build_generation_response_parses_json_embedded_in_text() -> None:
    request = _dummy_request()
    text = 'prefix\n{"title": "T", "body": ["line1", "line2"], "note": null, "intent": "overview"}\nsuffix'

    result = build_generation_response(text, request, model="mock-local")

    assert result.title == "T"
    assert result.body == ["line1", "line2"]
    assert result.intent == "overview"
    assert result.warnings == []


def test_build_generation_response_handles_non_json() -> None:
    request = _dummy_request()
    text = "bullet1\nbullet2"

    result = build_generation_response(text, request, model="mock-local")

    assert result.warnings and "response_not_json" in result.warnings
    assert result.body == ["bullet2"]


def test_build_slide_match_response_unknown_id_warns() -> None:
    request = SlideMatchRequest(
        card_id="card-1",
        card_chapter=None,
        card_intent=(),
        card_story_phase=None,
        card_summary="summary",
        prompt="prompt",
        system_prompt="system",
        candidates=[SlideMatchCandidate(slide_id="known")],
    )
    text = '{"slide_id": "unknown", "confidence": 0.8}'

    result = build_slide_match_response(text, request, model="mock-local")

    assert result.slide_id is None
    assert "unknown_slide_id" in result.warnings
    assert result.confidence == 0.0


def test_normalize_body_truncates_and_wraps() -> None:
    long_line = "x" * (MAX_BODY_LINE_LENGTH + 5)
    candidates = [long_line for _ in range(MAX_BODY_LINES + 2)]

    normalized, warnings = _normalize_body(candidates)

    assert len(normalized) == MAX_BODY_LINES
    assert "body_wrapped" in warnings

def test_normalize_body_preserves_blank_lines() -> None:
    candidates = ["line1\n\nline2"]

    normalized, warnings = _normalize_body(candidates)

    assert normalized[:3] == ["line1", "", "line2"]
    assert "body_wrapped" not in warnings
    assert "body_truncated" not in warnings

