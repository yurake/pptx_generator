"""LLM 応答の JSON 抽出ユーティリティ。"""

from __future__ import annotations

import json
import re
from typing import Any

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)


def strip_code_fences(text: str) -> str:
    """```json ... ``` 形式のコードフェンスを取り除く。"""
    if "```" not in text:
        return text
    match = _CODE_FENCE_RE.search(text)
    if match:
        return match.group(1)
    lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
    return "\n".join(lines)


def extract_json_value(text: str) -> Any:
    """テキストから JSON 値を抽出する。コードフェンスや前後ノイズを許容する。"""
    cleaned = strip_code_fences(text).strip()
    if not cleaned:
        raise json.JSONDecodeError("Empty JSON", text, 0)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char not in "{[":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[index:])
            return value
        except json.JSONDecodeError:
            continue

    raise json.JSONDecodeError("No JSON value found", cleaned, 0)


def extract_json_object(text: str) -> dict[str, Any]:
    """テキストから JSON オブジェクトを抽出する。"""
    value = extract_json_value(text)
    if isinstance(value, dict):
        return value
    raise json.JSONDecodeError("JSON object expected", text, 0)


__all__ = ["extract_json_object", "extract_json_value", "strip_code_fences"]
