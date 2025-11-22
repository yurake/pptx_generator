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
    "version": "2.0",
    "intent": [
        {
            "tag": "title",
            "label_jp": "表紙",
            "description": "表紙やタイトル専用のレイアウト。最低限のテキストと視覚要素のみで構成される。",
            "synonyms": ["cover", "front", "headline", "opening"],
            "examples": ["イントロダクション（社名＋スローガン）"],
            "deprecated": False,
        },
        {
            "tag": "agenda",
            "label_jp": "アジェンダ",
            "description": "章構成や議題を一覧表示するレイアウト。目次スライドを想定。",
            "synonyms": ["table_of_contents", "toc"],
            "examples": ["本日の流れ"],
            "deprecated": False,
        },
        {
            "tag": "overview",
            "label_jp": "概要",
            "description": "全体像や要約を提示するレイアウト。エグゼクティブサマリーやハイライトページを想定。",
            "synonyms": ["introduction"],
            "examples": ["プロジェクト概要"],
            "deprecated": False,
        },
        {
            "tag": "content",
            "label_jp": "本文",
            "description": "汎用的な本文ページで、テキストや図を柔軟に配置できるレイアウト。",
            "synonyms": ["body", "text", "details"],
            "examples": ["施策詳細", "提案背景"],
            "deprecated": False,
        },
        {
            "tag": "section_break",
            "label_jp": "セクション区切り",
            "description": "章区切りやセクション開始を示すレイアウト。章タイトルと簡単な補足情報を含む。",
            "synonyms": ["chapter_break"],
            "examples": ["第2章開始"],
            "deprecated": False,
        },
        {
            "tag": "closing",
            "label_jp": "クロージング",
            "description": "まとめ・連絡先など締めのメッセージを配置するレイアウト。",
            "synonyms": ["outro"],
            "examples": ["ご清聴ありがとうございました"],
            "deprecated": False,
        },
        {
            "tag": "summary",
            "label_jp": "要約",
            "description": "要点を箇条書きでまとめるレイアウト。結論や主要メッセージを短く整理する。",
            "synonyms": ["recap"],
            "examples": ["まとめ", "キーメッセージ"],
            "deprecated": False,
        },
        {
            "tag": "next_steps",
            "label_jp": "次のアクション",
            "description": "次のステップやスケジュールを提示するレイアウト。ロードマップやタスクを想定。",
            "synonyms": ["action_items"],
            "examples": ["今後の進め方"],
            "deprecated": False,
        },
        {
            "tag": "call_to_action",
            "label_jp": "CTA",
            "description": "提案の承認や連絡先など、読者に具体的な行動を促すレイアウト。",
            "synonyms": ["cta"],
            "examples": ["お問い合わせ先"],
            "deprecated": False,
        },
    ],
    "media": [
        {
            "tag": "chart",
            "label_jp": "チャート",
            "description": "グラフやチャートの配置を想定したレイアウト。",
            "synonyms": ["graph", "diagram"],
            "examples": ["売上推移チャート"],
            "deprecated": False,
        },
        {
            "tag": "table",
            "label_jp": "テーブル",
            "description": "テーブルや表形式のデータ配置を想定したレイアウト。",
            "synonyms": ["grid"],
            "examples": ["比較表", "指標一覧"],
            "deprecated": False,
        },
        {
            "tag": "visual",
            "label_jp": "ビジュアル",
            "description": "画像や図版を中心に配置するレイアウト。",
            "synonyms": ["picture", "image", "photo", "illustration"],
            "examples": ["製品写真", "概念図"],
            "deprecated": False,
        },
    ],
    "fallback": {
        "tag": "generic",
        "description": "用途が特定できない場合に使用するフォールバックタグ。",
        "synonyms": [],
        "examples": [],
        "deprecated": False,
    },
    "layout_rules": {
        "intent": [
            {"layout_name_pattern": ".*Title.*", "tags": ["title"]},
            {"layout_name_pattern": ".*Agenda.*", "tags": ["agenda"]},
            {"layout_name_pattern": ".*executive.*summary.*", "tags": ["overview", "content"]},
            {"layout_name_pattern": None, "tags": ["content"]},
        ],
        "media": [
            {"layout_name_pattern": ".*Chart.*", "tags": ["chart"]},
            {"layout_name_pattern": ".*Table.*", "tags": ["table"]},
            {"layout_name_pattern": ".*Picture.*", "tags": ["visual"]},
        ],
    },
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

    for parent in Path(__file__).resolve().parents:
        candidate = parent / "config" / "usage_tags.json"
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")

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
    """Return the raw usage tag configuration dictionary."""
    config = _load_config()
    return json.loads(json.dumps(config))


_INTENT_CATALOG: list[dict[str, object]] = []
_MEDIA_CATALOG: list[dict[str, object]] = []
_FALLBACK_ENTRY: dict[str, object] | None = None
_LAYOUT_RULES: dict[str, list[dict[str, object]]] = {"intent": [], "media": []}
_CANONICAL_INTENT_TAGS: frozenset[str] = frozenset()
_CANONICAL_MEDIA_TAGS: frozenset[str] = frozenset()
_CANONICAL_USAGE_TAGS: frozenset[str] = frozenset()
_SYNONYM_MAP: dict[str, str] = {}


def _normalize_tag_entry(entry: object) -> dict[str, object] | None:
    if not isinstance(entry, dict):
        return None
    raw_tag = entry.get("tag")
    if not isinstance(raw_tag, str):
        return None
    tag = raw_tag.strip().casefold()
    if not tag:
        return None

    def _collect_list(items: object, *, casefold: bool = False) -> list[str]:
        values: list[str] = []
        if isinstance(items, (list, tuple, set)):
            for item in items:
                if not isinstance(item, str):
                    continue
                value = item.strip()
                if not value:
                    continue
                values.append(value.casefold() if casefold else value)
        return values

    return {
        "tag": tag,
        "label": str(entry.get("label") or entry.get("label_jp") or ""),
        "description": str(entry.get("description") or ""),
        "synonyms": _collect_list(entry.get("synonyms"), casefold=True),
        "examples": _collect_list(entry.get("examples")),
        "deprecated": bool(entry.get("deprecated", False)),
    }


def _initialize_catalog() -> None:
    global _INTENT_CATALOG
    global _MEDIA_CATALOG
    global _FALLBACK_ENTRY
    global _LAYOUT_RULES
    global _CANONICAL_INTENT_TAGS
    global _CANONICAL_MEDIA_TAGS
    global _CANONICAL_USAGE_TAGS
    global _SYNONYM_MAP

    config = _load_config()

    intent_entries = []
    for entry in config.get("intent") or []:
        normalized = _normalize_tag_entry(entry)
        if normalized:
            intent_entries.append(normalized)

    media_entries = []
    for entry in config.get("media") or []:
        normalized = _normalize_tag_entry(entry)
        if normalized:
            media_entries.append(normalized)

    fallback_entry = None
    if isinstance(config.get("fallback"), dict):
        fallback_entry = _normalize_tag_entry(config["fallback"])

    synonym_map: dict[str, str] = {}
    for catalog_entry in intent_entries + media_entries:
        canonical = catalog_entry["tag"]
        synonym_map[canonical] = canonical
        for synonym in catalog_entry["synonyms"]:
            synonym_map[synonym] = canonical
    if fallback_entry is not None:
        canonical = fallback_entry["tag"]
        synonym_map[canonical] = canonical
        for synonym in fallback_entry["synonyms"]:
            synonym_map[synonym] = canonical

    layout_rules_raw = config.get("layout_rules") or {}
    normalized_layout_rules: dict[str, list[dict[str, object]]] = {"intent": [], "media": []}
    for section in ("intent", "media"):
        rules = layout_rules_raw.get(section) or []
        if not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            pattern = rule.get("layout_name_pattern")
            raw_tags = rule.get("tags") or []
            if not isinstance(raw_tags, list):
                continue
            canonical_tags = []
            for tag in raw_tags:
                canonical = None
                if isinstance(tag, str):
                    lookup = tag.strip().casefold()
                    canonical = synonym_map.get(lookup, lookup if lookup in synonym_map else None)
                if canonical:
                    canonical_tags.append(canonical)
            if canonical_tags:
                normalized_layout_rules[section].append(
                    {
                        "layout_name_pattern": pattern,
                        "tags": canonical_tags,
                    }
                )

    _INTENT_CATALOG = intent_entries
    _MEDIA_CATALOG = media_entries
    _FALLBACK_ENTRY = fallback_entry
    _LAYOUT_RULES = normalized_layout_rules
    _SYNONYM_MAP = synonym_map

    _CANONICAL_INTENT_TAGS = frozenset(entry["tag"] for entry in intent_entries if not entry["deprecated"])
    _CANONICAL_MEDIA_TAGS = frozenset(entry["tag"] for entry in media_entries if not entry["deprecated"])

    usage_tags = set(_CANONICAL_INTENT_TAGS) | set(_CANONICAL_MEDIA_TAGS)
    if fallback_entry and not fallback_entry["deprecated"]:
        usage_tags.add(fallback_entry["tag"])
    _CANONICAL_USAGE_TAGS = frozenset(usage_tags)


def get_usage_tag_catalog() -> dict[str, object]:
    """Return normalized usage tag catalog (intent/media/fallback)."""
    return {
        "intent": json.loads(json.dumps(_INTENT_CATALOG)),
        "media": json.loads(json.dumps(_MEDIA_CATALOG)),
        "fallback": json.loads(json.dumps(_FALLBACK_ENTRY)) if _FALLBACK_ENTRY is not None else None,
    }


def get_layout_rules() -> dict[str, list[dict[str, object]]]:
    """Return normalized layout rules for intent/media."""
    return json.loads(json.dumps(_LAYOUT_RULES))


def get_canonical_intent_tags() -> Tuple[str, ...]:
    return tuple(sorted(_CANONICAL_INTENT_TAGS))


def get_canonical_media_tags() -> Tuple[str, ...]:
    return tuple(sorted(_CANONICAL_MEDIA_TAGS))


def _deduplicate_preserve_order(tags: Iterable[str]) -> Tuple[str, ...]:
    ordered = OrderedDict()
    for tag in tags:
        ordered.setdefault(tag, None)
    return tuple(ordered.keys())


def _normalise_single_tag(tag: str | None) -> tuple[str | None, str | None]:
    if tag is None:
        return None, None

    cleaned = str(tag).strip().casefold()
    if not cleaned:
        return None, None

    mapped = _SYNONYM_MAP.get(cleaned, cleaned)
    if mapped in _CANONICAL_USAGE_TAGS:
        return mapped, None
    return None, mapped


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


_initialize_catalog()
CANONICAL_USAGE_TAGS: frozenset[str] = _CANONICAL_USAGE_TAGS


__all__ = [
    "CANONICAL_USAGE_TAGS",
    "get_usage_tag_catalog",
    "get_layout_rules",
    "get_usage_tag_config",
    "normalize_usage_tag_value",
    "normalize_usage_tags",
    "normalize_usage_tags_with_unknown",
]
