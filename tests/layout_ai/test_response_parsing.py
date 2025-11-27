"""layout_ai.client のレスポンス解析ヘルパーを検証するテスト。"""

from __future__ import annotations

import json

import pytest

from pptx_generator.layout_ai.client import (
    LayoutAIResponse,
    _coerce_tag_candidates,
    _deduplicate_tags,
    _extract_json_object,
    _parse_layout_response,
)


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
