"""レイアウトカタログの読み込み。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ...models import PipelineFallbackError
from ...utils.usage_tags import normalize_usage_tags
from .types import LayoutProfile
from ..table_anchor import normalize_placeholders

logger = logging.getLogger(__name__)


def load_layout_catalog(path: Path | None) -> dict[str, LayoutProfile]:
    """layouts.jsonl を解析し、LayoutProfile の辞書を返す。"""
    if path is None:
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        msg = f"layouts.jsonl が見つかりません: {path}"
        logger.error(msg)
        raise PipelineFallbackError(msg) from exc

    catalog: dict[str, LayoutProfile] = {}
    for line in text.splitlines():
        payload = _parse_line(line)
        if payload is None:
            continue
        profile = _build_profile(payload)
        catalog[profile.layout_id] = profile
        layout_name = profile.layout_name
        if layout_name and layout_name != profile.layout_id:
            existing = catalog.get(layout_name)
            if existing is None:
                catalog[layout_name] = profile
            elif existing.layout_id != profile.layout_id:
                logger.warning(
                    "layouts.jsonl の layout_name が重複しています: %s (layout_id=%s)",
                    layout_name,
                    profile.layout_id,
                )
    return catalog


def _parse_line(line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped:
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        logger.debug("layouts.jsonl のレコード解析に失敗しました: %s", stripped)
        return None
    if not isinstance(payload, dict):
        return None
    if not payload.get("layout_id"):
        return None
    return payload


def _build_profile(payload: dict[str, Any]) -> LayoutProfile:
    layout_id = payload["layout_id"]
    usage_tags = normalize_usage_tags(payload.get("usage_tags", []))

    layout_name = payload.get("layout_name") or layout_id
    layout_description = _extract_layout_description(payload.get("meta"))

    text_hint = payload.get("text_hint") or {}
    if not isinstance(text_hint, dict):
        text_hint = {}
    media_hint = payload.get("media_hint") or {}
    if not isinstance(media_hint, dict):
        media_hint = {}

    placeholder_records = payload.get("placeholders") or []
    if not isinstance(placeholder_records, list):
        placeholder_records = []
    normalized_placeholders = normalize_placeholders(placeholder_records)

    return LayoutProfile(
        layout_id=layout_id,
        layout_name=layout_name,
        usage_tags=usage_tags,
        text_hint=text_hint,
        media_hint=media_hint,
        layout_description=layout_description,
        placeholders=normalized_placeholders,
    )


def _extract_layout_description(meta_info: Any) -> dict[str, Any] | None:
    if not isinstance(meta_info, dict):
        return None
    description_value = meta_info.get("layout_description")
    if isinstance(description_value, dict):
        return description_value
    if isinstance(description_value, str):
        stripped = description_value.strip()
        if stripped:
            return {
                "overview": stripped,
                "elements": [],
            }
    return None
