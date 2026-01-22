from __future__ import annotations

import json

import pytest

from pptx_generator.llm.json_utils import extract_json_object, extract_json_value, strip_code_fences


def test_strip_code_fences_extracts_payload() -> None:
    text = "```json\n{\"a\": 1}\n```"
    assert json.loads(strip_code_fences(text)) == {"a": 1}


def test_extract_json_object_handles_code_fence() -> None:
    text = "```json\n{\"a\": 1}\n```"
    assert extract_json_object(text) == {"a": 1}


def test_extract_json_value_handles_embedded_json() -> None:
    text = "prefix\n{\"a\": 1}\nsuffix"
    assert extract_json_object(text) == {"a": 1}


def test_extract_json_value_handles_array() -> None:
    text = "prefix\n[1, 2]\nsuffix"
    assert extract_json_value(text) == [1, 2]


def test_extract_json_object_rejects_array() -> None:
    with pytest.raises(json.JSONDecodeError):
        extract_json_object("[1, 2]")
