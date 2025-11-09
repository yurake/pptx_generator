"""Utilities for handling layout usage tags consistently."""

from __future__ import annotations

from collections import OrderedDict
from typing import Iterable, Tuple

CANONICAL_USAGE_TAGS: frozenset[str] = frozenset(
    {
        "agenda",
        "chart",
        "content",
        "overview",
        "table",
        "title",
        "visual",
        "generic",
    }
)

_SYNONYM_MAP: dict[str, str] = {
    "body": "content",
    "text": "content",
    "picture": "visual",
    "image": "visual",
    "photo": "visual",
    "cover": "title",
    "front": "title",
    "summary": "overview",
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
]
