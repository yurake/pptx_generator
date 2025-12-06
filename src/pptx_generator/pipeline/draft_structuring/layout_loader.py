"""Utilities for loading layout profiles."""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from ...draft_recommender import LayoutProfile
from ...utils.usage_tags import normalize_usage_tags
from ..table_anchor import normalize_placeholders
from .errors import DraftStructuringError

logger = logging.getLogger(__name__)


def load_layouts(
    *,
    path: Path | None,
    spec_source_path: Path | None,
) -> list[LayoutProfile]:
    if path is None:
        source_hint = str(spec_source_path) if spec_source_path is not None else "in-memory JobSpec"
        logger.info(
            "layouts.jsonl が指定されていないため、JobSpec (%s) の layout を基準にしたヒューリスティック候補を使用します",
            source_hint,
        )
        return []

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        msg = f"layouts.jsonl を読み込めません: {path}"
        raise DraftStructuringError(msg) from exc

    records: list[LayoutProfile] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            msg = f"layouts.jsonl の解析に失敗しました: {path}"
            raise DraftStructuringError(msg) from exc

        layout_id = payload.get("layout_id")
        if not layout_id:
            logger.debug("layout_id が存在しないレコードをスキップ: %s", payload)
            continue

        text_hint = payload.get("text_hint") or {}
        media_hint = payload.get("media_hint") or {}
        if not isinstance(text_hint, dict):
            text_hint = {}
        if not isinstance(media_hint, dict):
            media_hint = {}

        placeholder_records = payload.get("placeholders") or []
        if not isinstance(placeholder_records, list):
            placeholder_records = []
        normalized_placeholders = normalize_placeholders(placeholder_records)
        placeholder_summary = payload.get("placeholder_summary")
        if not isinstance(placeholder_summary, dict):
            placeholder_summary = summarize_placeholders(placeholder_records)

        heuristic_info = payload.get("heuristic")
        if not isinstance(heuristic_info, dict):
            heuristic_info = {}
        blueprint_info = payload.get("blueprint")
        if not isinstance(blueprint_info, dict):
            blueprint_info = {}
        meta_info = payload.get("meta")
        if not isinstance(meta_info, dict):
            meta_info = {}

        layout_description = None
        description_value = meta_info.get("layout_description")
        if isinstance(description_value, dict):
            layout_description = description_value
        elif isinstance(description_value, str):
            stripped = description_value.strip()
            if stripped:
                layout_description = {
                    "overview": stripped,
                    "elements": [],
                }

        records.append(
            LayoutProfile(
                layout_id=layout_id,
                layout_name=payload.get("layout_name") or layout_id,
                usage_tags=normalize_usage_tags(payload.get("usage_tags", [])),
                text_hint=text_hint,
                media_hint=media_hint,
                placeholder_summary=placeholder_summary,
                heuristic=heuristic_info,
                blueprint=blueprint_info,
                meta=meta_info,
                layout_description=layout_description,
                placeholders=normalized_placeholders,
            )
        )

    return records


def summarize_placeholders(placeholders: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not placeholders:
        return {}

    counts: Counter[str] = Counter()
    processed: list[tuple[float, dict[str, Any]]] = []
    total_area = 0.0
    type_area: defaultdict[str, float] = defaultdict(float)

    for placeholder in placeholders:
        raw_type = placeholder.get("type")
        p_type = str(raw_type or "").casefold()
        if not p_type:
            p_type = "unknown"
        counts[p_type] += 1

        bbox = placeholder.get("bbox") or {}
        width = float(bbox.get("width") or 0.0)
        height = float(bbox.get("height") or 0.0)
        area = max(width, 0.0) * max(height, 0.0)
        total_area += area
        type_area[p_type] += area

        shape_type = placeholder.get("shape_type")
        shape_type_str = str(shape_type or "").casefold() or None
        flags = placeholder.get("flags")
        flags_list = [str(flag) for flag in flags[:6]] if isinstance(flags, list) else []

        entry: dict[str, Any] = {
            "name": str(placeholder.get("name") or "")[:64],
            "type": p_type,
        }
        if shape_type_str:
            entry["shape_type"] = shape_type_str
        if flags_list:
            entry["flags"] = flags_list
        processed.append((area, entry))

    details: list[dict[str, Any]] = []
    for area, entry in sorted(processed, key=lambda item: item[0], reverse=True)[:8]:
        ratio = round(area / total_area, 3) if total_area > 0 else None
        entry = dict(entry)
        entry["area_ratio"] = ratio
        details.append(entry)

    area_ratio = {
        key: round(value / total_area, 3) for key, value in type_area.items() if total_area > 0
    }

    attributes = {
        "total": sum(counts.values()),
        "has_title": counts.get("title", 0) + counts.get("subtitle", 0) > 0,
        "has_body": counts.get("body", 0) + counts.get("content", 0) > 0,
        "has_table": counts.get("table", 0) > 0,
        "has_chart": counts.get("chart", 0) > 0,
        "has_visual": (
            counts.get("image", 0) + counts.get("media", 0) + counts.get("object", 0)
        )
        > 0,
    }

    return {
        "counts": {key: counts[key] for key in sorted(counts)},
        "area_ratio": area_ratio,
        "details": details,
        "attributes": attributes,
    }
