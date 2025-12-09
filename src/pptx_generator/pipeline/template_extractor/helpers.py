"""Shared helper utilities for the template extractor."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from pptx.dml.color import ColorFormat

from .constants import EMU_PER_INCH

__all__ = [
    "length_to_pt",
    "length_to_inches",
    "color_to_hex",
    "normalize_hex",
    "slugify_layout_name",
    "derive_template_id",
]


def length_to_pt(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value.pt)
    except AttributeError:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


def length_to_inches(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value.inches)
    except AttributeError:
        try:
            return float(value) / EMU_PER_INCH
        except (TypeError, ValueError, ZeroDivisionError):
            return None


def color_to_hex(color: ColorFormat | None) -> str | None:
    if color is None:
        return None
    rgb = getattr(color, "rgb", None)
    if rgb is None:
        return None
    try:
        components: Iterable[int] = tuple(rgb)  # type: ignore[arg-type]
    except TypeError:
        return None
    return "#" + "".join(f"{component:02X}" for component in components)


def normalize_hex(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text if text.startswith("#") else f"#{text}"


def slugify_layout_name(name: str | None) -> str:
    normalized = unicodedata.normalize("NFKC", (name or "").strip())
    normalized = normalized.replace(" ", "_")
    normalized = re.sub(r"[\s/\\]+", "_", normalized)
    normalized = re.sub(r"[^0-9A-Za-z_\-一-龯ぁ-んァ-ンー]+", "", normalized)
    return normalized.lower()


def derive_template_id(path: Path) -> str:
    stem = unicodedata.normalize("NFKC", path.stem)
    stem = re.sub(r"[^0-9A-Za-z_\-一-龯ぁ-んァ-ンー]+", "", stem)
    return stem or "template"
