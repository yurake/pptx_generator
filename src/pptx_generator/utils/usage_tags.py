"""Utilities for handling layout usage tags consistently."""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path
from typing import Iterable, Tuple

_CONFIG_PATH = Path("config/usage_tags.json")
_CONFIG_DATA: dict[str, object] | None = None


def _load_config() -> dict[str, object]:
    global _CONFIG_DATA
    if _CONFIG_DATA is None:
        if not _CONFIG_PATH.exists():
            raise FileNotFoundError(f"usage_tags config not found: {_CONFIG_PATH}")
        _CONFIG_DATA = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
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
