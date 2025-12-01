"""Analyzer スナップショットとの比較処理。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def compare_with_analyzer_snapshot(
    *,
    records: list[dict[str, Any]],
    template_id: str,
    snapshot_path: Path | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    if snapshot_path is None:
        return warnings, errors, issues

    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(
            {
                "code": "analyzer_snapshot_missing",
                "layout_id": "__analyzer__",
                "name": snapshot_path.name,
                "detail": "Analyzer スナップショットが見つかりません",
            }
        )
        return warnings, errors, issues
    except json.JSONDecodeError as exc:
        errors.append(
            {
                "code": "analyzer_snapshot_invalid",
                "layout_id": "__analyzer__",
                "name": snapshot_path.name,
                "detail": f"JSON デコードに失敗しました ({exc})",
            }
        )
        return warnings, errors, issues

    slides = payload.get("slides", [])
    template_layout_anchors: dict[str, set[str]] = {}
    layout_name_to_id: dict[str, str] = {}
    for record in records:
        layout_name = record["layout_name"]
        layout_id = record["layout_id"]
        layout_name_to_id[layout_name] = layout_id
        anchors = {
            placeholder["name"]
            for placeholder in record["placeholders"]
            if placeholder["name"]
        }
        template_layout_anchors[layout_name] = anchors

    snapshot_layout_anchors: dict[str, set[str]] = {}
    anchor_sources: dict[str, dict[str, str]] = {}

    for slide in slides:
        layout_name = slide.get("layout")
        slide_id = slide.get("slide_id", "unknown")
        placeholders = slide.get("placeholders", [])
        named_shapes = slide.get("named_shapes", [])

        for placeholder in placeholders:
            name = (placeholder.get("name") or "").strip()
            if not name:
                display_name = placeholder.get("placeholder_type") or "__unnamed__"
                warnings.append(
                    {
                        "code": "analyzer_placeholder_unnamed",
                        "layout_id": layout_name or "__unknown__",
                        "name": display_name,
                        "detail": f"slide={slide_id}",
                    }
                )
                continue
            snapshot_layout_anchors.setdefault(layout_name, set()).add(name)
            anchor_sources.setdefault(layout_name, {}).setdefault(name, slide_id)

        for shape in named_shapes:
            name = (shape.get("name") or "").strip()
            if not name:
                continue
            snapshot_layout_anchors.setdefault(layout_name, set()).add(name)
            anchor_sources.setdefault(layout_name, {}).setdefault(name, slide_id)

    for layout_name, template_anchors in template_layout_anchors.items():
        snapshot_anchors = snapshot_layout_anchors.get(layout_name, set())
        missing = sorted(template_anchors - snapshot_anchors)
        for anchor in missing:
            layout_id = layout_name_to_id.get(layout_name)
            if layout_id is None:
                layout_id = layout_name or "__unknown__"
            entry = {
                "code": "analyzer_anchor_missing",
                "layout_id": layout_id,
                "name": anchor,
                "detail": "Analyzer スナップショットに対応するアンカーがありません",
            }
            warnings.append(entry)
            issues.append(
                {
                    "code": "analyzer_anchor_missing",
                    "layout_id": layout_id,
                    "detail": entry["detail"],
                    "anchor": anchor,
                }
            )

    for layout_name, snapshot_anchors in snapshot_layout_anchors.items():
        template_anchors = template_layout_anchors.get(layout_name, set())
        extra = sorted(snapshot_anchors - template_anchors)
        for anchor in extra:
            source_slide = anchor_sources.get(layout_name, {}).get(anchor)
            detail = f"slide={source_slide}" if source_slide else None
            layout_id = layout_name_to_id.get(layout_name)
            if layout_id is None:
                layout_id = layout_name or "__unknown__"
            entry: dict[str, Any] = {
                "code": "analyzer_anchor_unexpected",
                "layout_id": layout_id,
                "name": anchor,
            }
            if detail:
                entry["detail"] = detail
            warnings.append(entry)
            issues.append(
                {
                    "code": "analyzer_anchor_unexpected",
                    "layout_id": layout_id,
                    "detail": detail or "",
                    "anchor": anchor,
                }
            )

        if layout_name not in template_layout_anchors:
            warnings.append(
                {
                    "code": "analyzer_layout_unknown",
                    "layout_id": layout_name or "__unknown__",
                    "name": template_id,
                    "detail": "テンプレ抽出結果に存在しないレイアウトです",
                }
            )

    return warnings, errors, issues
