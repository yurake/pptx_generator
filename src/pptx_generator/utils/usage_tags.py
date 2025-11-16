"""Utilities for handling layout usage tags consistently."""

from __future__ import annotations

import json
import logging
import os
from collections import OrderedDict
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Iterable, Tuple

logger = logging.getLogger(__name__)

_CONFIG_DATA: dict[str, object] | None = None

DEFAULT_USAGE_TAG_CONFIG: dict[str, object] = {
    "intent_tags": [
        {
            "tag": "title",
            "description": "表紙やタイトル専用のレイアウト。最低限のテキストと視覚要素のみで構成される。",
        },
        {
            "tag": "agenda",
            "description": "章構成や議題を一覧表示するレイアウト。目次スライドを想定。",
        },
        {
            "tag": "overview",
            "description": "全体像や要約を提示するレイアウト。エグゼクティブサマリーやハイライトページを想定。",
        },
        {
            "tag": "content",
            "description": "汎用的な本文ページで、テキストや図を柔軟に配置できるレイアウト。",
        },
        {
            "tag": "section_break",
            "description": "章区切りやセクション開始を示すレイアウト。章タイトルと簡単な補足情報を含む。",
        },
        {
            "tag": "closing",
            "description": "クロージングやまとめのレイアウト。感謝のメッセージや呼びかけを想定。",
        },
        {
            "tag": "summary",
            "description": "要点を箇条書きでまとめるレイアウト。結論や主要メッセージを短く整理。",
        },
        {
            "tag": "next_steps",
            "description": "次のアクションやスケジュールを提示するレイアウト。ロードマップやタスクを想定。",
        },
        {
            "tag": "call_to_action",
            "description": "提案の承認や連絡先など、読者に具体的な行動を促すレイアウト。",
        },
    ],
    "media_tags": [
        {
            "tag": "chart",
            "description": "グラフやチャートの配置を想定したレイアウト。",
        },
        {
            "tag": "table",
            "description": "テーブルや表形式のデータ配置を想定したレイアウト。",
        },
        {
            "tag": "visual",
            "description": "画像や図版を中心に配置するレイアウト。",
        },
    ],
    "fallback_tag": {
        "tag": "generic",
        "description": "用途が特定できない場合のフォールバックタグ。",
    },
    "static_rules": [
        {"layout_name_pattern": ".*Title.*", "tags": ["title"]},
        {"layout_name_pattern": ".*Agenda.*", "tags": ["agenda"]},
        {
            "layout_name_pattern": ".*executive.*summary.*",
            "tags": ["overview", "content"],
        },
        {"layout_name_pattern": None, "tags": ["content"]},
    ],
}


def _read_config_text() -> str | None:
    env_path = os.getenv("PPTX_GENERATOR_USAGE_TAGS")
    if env_path:
        path = Path(env_path)
        if path.is_file():
            return path.read_text(encoding="utf-8")

    try:
        resource = importlib_resources.files("pptx_generator").joinpath("config/usage_tags.json")
        if resource.is_file():
            return resource.read_text(encoding="utf-8")
    except (ModuleNotFoundError, FileNotFoundError, AttributeError):  # pragma: no cover - optional path
        pass

    repo_path = Path(__file__).resolve().parents[2] / "config" / "usage_tags.json"
    if repo_path.is_file():
        return repo_path.read_text(encoding="utf-8")

    return None


def _load_config() -> dict[str, object]:
    global _CONFIG_DATA
    if _CONFIG_DATA is not None:
        return _CONFIG_DATA

    raw_text = _read_config_text()
    if raw_text is not None:
        try:
            _CONFIG_DATA = json.loads(raw_text)
            return _CONFIG_DATA
        except json.JSONDecodeError as exc:
            logger.warning("usage_tags config JSON decode failed: %s", exc)

    logger.warning("usage_tags config not found, falling back to default definition")
    _CONFIG_DATA = DEFAULT_USAGE_TAG_CONFIG
    return _CONFIG_DATA


def get_usage_tag_config() -> dict[str, object]:
    """Return the usage tag configuration dictionary."""
    config = _load_config()
    return json.loads(json.dumps(config))


def _extract_tag_list(entries: list[object]) -> list[str]:
    tags: list[str] = []
    for entry in entries:
        if isinstance(entry, str):
            value = entry.strip().casefold()
            if value:
                tags.append(value)
        elif isinstance(entry, dict):
            tag_value = entry.get("tag")
            if isinstance(tag_value, str):
                value = tag_value.strip().casefold()
                if value:
                    tags.append(value)
    return tags


def _build_canonical_tags() -> frozenset[str]:
    config = _load_config()
    intent_tags = _extract_tag_list(config.get("intent_tags") or [])
    media_tags = _extract_tag_list(config.get("media_tags") or [])
    fallback = config.get("fallback_tag")
    tags = set(intent_tags) | set(media_tags)
    if isinstance(fallback, str):
        value = fallback.strip().casefold()
        if value:
            tags.add(value)
    elif isinstance(fallback, dict):
        tag_value = fallback.get("tag")
        if isinstance(tag_value, str):
            value = tag_value.strip().casefold()
            if value:
                tags.add(value)
    return frozenset(tags)


CANONICAL_USAGE_TAGS: frozenset[str] = _build_canonical_tags()

_SYNONYM_MAP: dict[str, str] = {
    "body": "content",
    "text": "content",
    "picture": "visual",
    "image": "visual",
    "photo": "visual",
    "cover": "title",
    "front": "title",
    "summary": "overview",
    "kpi": "content",
    "metric": "content",
}


def _normalise_single_tag(tag: str | None) -> tuple[str | None, str | None]:
    if tag is None:
        return None, None

    cleaned = str(tag).strip().casefold()
    if not cleaned:
        return None, None

    mapped = _SYNONYM_MAP.get(cleaned, cleaned)
    if mapped in CANONICAL_USAGE_TAGS:
        return mapped, None
    return None, mapped


def _deduplicate_preserve_order(tags: Iterable[str]) -> Tuple[str, ...]:
    ordered = OrderedDict()
    for tag in tags:
        ordered.setdefault(tag, None)
    return tuple(ordered.keys())


def normalize_usage_tag_value(tag: str | None) -> str | None:
    canonical, _ = _normalise_single_tag(tag)
    return canonical


def normalize_usage_tags(tags: Iterable[str | None]) -> Tuple[str, ...]:
    normalised, _ = normalize_usage_tags_with_unknown(tags)
    return normalised


def normalize_usage_tags_with_unknown(
    tags: Iterable[str | None],
) -> tuple[Tuple[str, ...], set[str]]:
    normalised: list[str] = []
    unknown: set[str] = set()

    for tag in tags:
        canonical, unknown_value = _normalise_single_tag(tag)
        if canonical:
            normalised.append(canonical)
        if unknown_value and unknown_value not in CANONICAL_USAGE_TAGS:
            unknown.add(unknown_value)

    return _deduplicate_preserve_order(normalised), unknown


__all__ = [
    "CANONICAL_USAGE_TAGS",
    "normalize_usage_tag_value",
    "normalize_usage_tags",
    "normalize_usage_tags_with_unknown",
    "get_usage_tag_config",
]
