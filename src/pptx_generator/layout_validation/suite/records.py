"""レイアウトレコード構築関連のユーティリティ。"""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Sequence

from ...models import LayoutInfo, ShapeInfo, TemplateBlueprint
from ...utils.layout_metadata import (
    HeuristicUsageTagsResult,
    derive_usage_tags,
    normalise_placeholder_type,
)
from .constants import EMU_PER_INCH, IMAGE_PLACEHOLDER_TYPES, TEXT_PLACEHOLDER_TYPES


def collect_placeholder_records(
    *,
    layout: LayoutInfo,
    layout_id: str,
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    names: list[str] = []
    warnings: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for shape in layout.anchors:
        if not should_include_shape(shape):
            continue

        normalised_type = normalise_placeholder_type(shape.placeholder_type, shape.name)
        bbox = shape_bbox(shape)
        style_hint = build_style_hint(shape)
        flags = build_flags(shape, normalised_type)

        if bbox["x"] < 0 or bbox["y"] < 0:
            warnings.append(
                {
                    "code": "placeholder_negative_origin",
                    "layout_id": layout_id,
                    "name": shape.name,
                    "detail": f"x={bbox['x']} y={bbox['y']}",
                }
            )

        capacity_payload = (
            shape.text_capacity.model_dump()
            if getattr(shape, "text_capacity", None)
            else None
        )

        records.append(
            {
                "name": shape.name,
                "type": normalised_type,
                "bbox": bbox,
                "style_hint": style_hint,
                "shape_type": shape.shape_type,
                "flags": flags,
                "text_capacity": capacity_payload,
            }
        )
        names.append(shape.name)

        if shape.missing_fields:
            errors.append(
                {
                    "code": "missing_fields",
                    "layout_id": layout_id,
                    "name": shape.name,
                    "detail": ", ".join(shape.missing_fields),
                }
            )
        if shape.error:
            errors.append(
                {
                    "code": "shape_extract_error",
                    "layout_id": layout_id,
                    "name": shape.name,
                    "detail": shape.error,
                }
            )

        if normalised_type == "unknown":
            warnings.append(
                {
                    "code": "placeholder_unknown_type",
                    "layout_id": layout_id,
                    "name": shape.name,
                }
            )

    return records, names, warnings, errors


def detect_duplicate_placeholder_warnings(
    *,
    layout_id: str,
    placeholder_names: Sequence[str],
) -> list[dict[str, Any]]:
    duplicates = [name for name, count in Counter(placeholder_names).items() if count > 1]
    return [
        {
            "code": "duplicate_placeholder",
            "layout_id": layout_id,
            "name": name,
        }
        for name in duplicates
    ]


def build_heuristic_usage_result(
    layout: LayoutInfo,
    placeholder_records: Sequence[dict[str, Any]],
) -> HeuristicUsageTagsResult:
    if layout.heuristic:
        return HeuristicUsageTagsResult(
            tags=set(layout.heuristic.get("tags") or []),
            has_title_placeholder=bool(layout.heuristic.get("has_title_placeholder")),
            has_body_placeholder=bool(layout.heuristic.get("has_body_placeholder")),
            title_from_name=bool(layout.heuristic.get("title_from_name")),
            reasons=list(layout.heuristic.get("reasons") or []),
        )
    return derive_usage_tags(layout.name or "", placeholder_records)


def derive_text_hint(placeholders: Iterable[dict[str, Any]]) -> dict[str, int]:
    max_chars = 0
    max_lines = 0
    for placeholder in placeholders:
        p_type = placeholder.get("type")
        if p_type not in TEXT_PLACEHOLDER_TYPES:
            continue

        capacity = placeholder.get("text_capacity")
        if capacity:
            max_lines += int(capacity.get("max_lines") or 0)
            max_chars += int(capacity.get("total_chars") or 0)
            continue

        bbox = placeholder["bbox"]
        width_in = bbox["width"] / EMU_PER_INCH
        height_in = bbox["height"] / EMU_PER_INCH
        approx_lines = max(int(height_in / 0.28), 1)
        approx_chars_per_line = max(int(width_in * 20), 10)
        max_lines += approx_lines
        max_chars += approx_lines * approx_chars_per_line

    return {
        "max_chars": max_chars,
        "max_lines": max_lines,
    }


def derive_media_hint(placeholders: Iterable[dict[str, Any]]) -> dict[str, bool]:
    allow_table = False
    allow_chart = False
    allow_image = False

    for placeholder in placeholders:
        p_type = placeholder.get("type")
        if p_type == "table":
            allow_table = True
        if p_type == "chart":
            allow_chart = True
        if p_type in IMAGE_PLACEHOLDER_TYPES:
            allow_image = True

    return {
        "allow_table": allow_table,
        "allow_chart": allow_chart,
        "allow_image": allow_image,
    }


def build_blueprint_lookup(
    blueprint: TemplateBlueprint | None,
) -> dict[str, dict[str, Any]]:
    if blueprint is None:
        return {}

    lookup: dict[str, dict[str, Any]] = {}
    for slide in blueprint.slides:
        layout_name = slide.layout
        if not layout_name:
            continue

        entry = lookup.setdefault(
            layout_name,
            {"layout": layout_name, "slides": [], "slots": []},
        )

        slide_entry = {
            "blueprint_slide_id": slide.slide_id,
            "required": slide.required,
            "intent_tags": sorted(slide.intent_tags),
        }
        entry["slides"].append(slide_entry)

        for slot in slide.slots:
            entry["slots"].append(
                {
                    "slot_id": slot.slot_id,
                    "anchor": slot.anchor,
                    "required": slot.required,
                    "content_type": slot.content_type,
                    "intent_tags": sorted(slot.intent_tags),
                }
            )

    for layout_name, entry in lookup.items():
        if entry["slides"]:
            entry["slides"] = sorted(
                entry["slides"],
                key=lambda item: item["blueprint_slide_id"],
            )
        else:
            entry.pop("slides")

        if entry["slots"]:
            unique_slots: dict[str, dict[str, Any]] = {}
            for slot_entry in entry["slots"]:
                unique_slots.setdefault(slot_entry["slot_id"], slot_entry)
            entry["slots"] = [
                unique_slots[key] for key in sorted(unique_slots)
            ]
        else:
            entry.pop("slots")

    return lookup


def should_include_shape(shape: ShapeInfo) -> bool:
    if shape.is_placeholder:
        return True
    if shape.placeholder_type:
        return True
    if shape.name and shape.name.lower() not in {"rectangle", "textbox"}:
        return True
    return False


def shape_bbox(shape: ShapeInfo) -> dict[str, int]:
    return {
        "x": int(round(shape.left_in * EMU_PER_INCH)),
        "y": int(round(shape.top_in * EMU_PER_INCH)),
        "width": int(round(shape.width_in * EMU_PER_INCH)),
        "height": int(round(shape.height_in * EMU_PER_INCH)),
    }


def build_style_hint(shape: ShapeInfo) -> dict[str, Any]:
    style_hint: dict[str, Any] = {}
    if shape.text:
        style_hint["sample_text"] = shape.text[:120]
    if shape.conflict:
        style_hint["conflict"] = shape.conflict
    return style_hint


def build_flags(shape: ShapeInfo, placeholder_type: str) -> list[str]:
    flags: list[str] = []
    if placeholder_type == "unknown":
        flags.append("unknown_type")
    if shape.conflict:
        flags.append("anchor_conflict")
    if shape.missing_fields:
        flags.append("missing_fields")
    return flags
