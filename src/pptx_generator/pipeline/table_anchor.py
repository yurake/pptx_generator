"""Utility helpers for mapping tables to layout placeholders."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence, Tuple

from ..models import ContentTableData, Slide

TABLE_NAME_KEYWORDS: tuple[str, ...] = (
    "table",
    "grid",
    "matrix",
    "sheet",
    "scorecard",
    "list",
    "data",
    "データ",
    "一覧",
    "表",
)
NEGATIVE_KEYWORDS: tuple[str, ...] = (
    "logo",
    "image",
    "photo",
    "chart",
    "グラフ",
    "ロゴ",
)
PREFERRED_TYPE_SCORE: Mapping[str, int] = {
    "table": 8,
    "content": 6,
    "body": 6,
    "text": 5,
    "object": 4,
}


def build_table_payload(table_data: ContentTableData) -> dict[str, Any]:
    """Convert ContentTableData into the payload expected by generate_ready."""

    return {
        "headers": list(table_data.headers),
        "rows": [list(row) for row in table_data.rows],
    }


def is_table_payload(value: object) -> bool:
    """Return True when the value looks like a table payload."""

    if not isinstance(value, dict):
        return False
    rows = value.get("rows")
    headers = value.get("headers")
    if not isinstance(rows, list) or not isinstance(headers, list):
        return False
    return True


def resolve_table_anchor(
    spec_slide: Slide | None,
    placeholders: Sequence[Mapping[str, Any]],
) -> tuple[str | None, list[str]]:
    """Resolve table anchor from spec slide or layout placeholders."""

    if spec_slide is not None:
        for table in spec_slide.tables:
            if table.anchor:
                return table.anchor, ["spec-anchor"]

    anchor, reasons = select_table_anchor(placeholders)
    return anchor, reasons


def select_table_anchor(
    placeholders: Sequence[Mapping[str, Any]],
) -> tuple[str | None, list[str]]:
    """Select the most suitable placeholder name for a table."""

    if not placeholders:
        return None, ["heuristic:no-placeholders"]

    scored: list[tuple[int, float, int, str, list[str]]] = []
    for index, placeholder in enumerate(placeholders):
        name = str(placeholder.get("name") or "").strip()
        if not name:
            continue
        name_lower = name.casefold()
        placeholder_type = str(placeholder.get("type") or "").casefold()

        if placeholder_type in {"image", "media", "chart", "picture"}:
            continue
        if any(keyword in name_lower for keyword in NEGATIVE_KEYWORDS):
            continue

        score = PREFERRED_TYPE_SCORE.get(placeholder_type, 2)
        reasons = [f"type:{placeholder_type or 'unknown'}"]

        if any(keyword in name_lower for keyword in TABLE_NAME_KEYWORDS):
            score += 12
            reasons.append("name:table-keyword")
        if "body" in name_lower:
            score += 5
            reasons.append("name:body")
        if any(keyword in name_lower for keyword in ("right", "右")):
            score += 3
            reasons.append("name:right")
        if any(keyword in name_lower for keyword in ("lower", "bottom", "下", "bottom")):
            score += 3
            reasons.append("name:lower")
        if any(keyword in name_lower for keyword in ("data", "value", "数値", "項目")):
            score += 2
            reasons.append("name:data")

        area_ratio_value = placeholder.get("area_ratio")
        area_ratio = float(area_ratio_value) if isinstance(area_ratio_value, (int, float)) else 0.0
        if area_ratio > 0:
            score += min(int(area_ratio * 20), 6)
            reasons.append(f"area:{area_ratio:.3f}")

        flags = placeholder.get("flags")
        if isinstance(flags, Iterable):
            normalized_flags = {str(flag).casefold() for flag in flags}
            if "anchor_conflict" in normalized_flags:
                score -= 3
                reasons.append("flag:anchor_conflict")

        scored.append((score, area_ratio, index, name, reasons))

    if not scored:
        return None, ["heuristic:no-candidates"]

    scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
    best_score, _, _, anchor_name, reasons = scored[0]
    if best_score <= 0:
        return None, ["heuristic:no-positive"]
    return anchor_name, [f"heuristic:{reason}" for reason in reasons]


def normalize_placeholders(
    placeholders: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Normalize raw placeholder payloads from layouts.jsonl."""

    normalized: list[dict[str, Any]] = []
    total_area = 0.0

    for index, placeholder in enumerate(placeholders):
        bbox = placeholder.get("bbox") or {}
        width = float(bbox.get("width") or 0.0)
        height = float(bbox.get("height") or 0.0)
        left = float(bbox.get("x") or 0.0)
        top = float(bbox.get("y") or 0.0)
        area = max(width, 0.0) * max(height, 0.0)

        flags_raw = placeholder.get("flags")
        if isinstance(flags_raw, (list, tuple)):
            flags = [str(flag) for flag in flags_raw[:6]]
        else:
            flags = []

        entry: dict[str, Any] = {
            "name": str(placeholder.get("name") or "")[:64],
            "type": str(placeholder.get("type") or "").casefold() or "unknown",
            "shape_type": str(placeholder.get("shape_type") or "").casefold() or None,
            "flags": flags,
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "area": area,
            "index": index,
        }
        normalized.append(entry)
        total_area += area

    if total_area > 0:
        for entry in normalized:
            entry["area_ratio"] = round(entry["area"] / total_area, 6)

    return tuple(normalized)
