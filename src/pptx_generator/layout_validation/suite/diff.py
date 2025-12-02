"""差分レポート生成。"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .io import load_jsonl
from .types import LayoutValidationError


def build_diff_report(
    *,
    records: list[dict[str, Any]],
    target_template_id: str,
    baseline_path: Path,
) -> dict[str, Any] | None:
    if not baseline_path.exists():
        raise LayoutValidationError(f"ベースラインが存在しません: {baseline_path}")

    baseline_records = load_jsonl(baseline_path)
    if not baseline_records:
        return {
            "baseline_template_id": None,
            "target_template_id": target_template_id,
            "layouts_added": [record["layout_id"] for record in records],
            "layouts_removed": [],
            "placeholders_changed": [],
            "issues": [],
        }

    current_map = {record["layout_id"]: record for record in records}
    baseline_map = {record["layout_id"]: record for record in baseline_records}

    layouts_added = sorted(set(current_map) - set(baseline_map))
    layouts_removed = sorted(set(baseline_map) - set(current_map))

    placeholders_changed: list[dict[str, str]] = []
    issues: list[dict[str, str]] = []

    for layout_id in sorted(set(current_map) & set(baseline_map)):
        current = current_map[layout_id]
        baseline = baseline_map[layout_id]
        current_placeholders = {
            placeholder["name"]: placeholder for placeholder in current["placeholders"]
        }
        baseline_placeholders = {
            placeholder["name"]: placeholder for placeholder in baseline["placeholders"]
        }

        added_names = sorted(set(current_placeholders) - set(baseline_placeholders))
        removed_names = sorted(set(baseline_placeholders) - set(current_placeholders))

        for name in added_names:
            issues.append(
                {
                    "code": "placeholder_added",
                    "layout_id": layout_id,
                    "detail": name,
                }
            )

        for name in removed_names:
            issues.append(
                {
                    "code": "placeholder_missing",
                    "layout_id": layout_id,
                    "detail": name,
                }
            )

        for name in sorted(set(current_placeholders) & set(baseline_placeholders)):
            current_placeholder = current_placeholders[name]
            baseline_placeholder = baseline_placeholders[name]

            if current_placeholder.get("type") != baseline_placeholder.get("type"):
                placeholders_changed.append(
                    {
                        "layout_id": layout_id,
                        "name": name,
                        "field": "type",
                    }
                )

            if not math.isclose(
                current_placeholder["bbox"]["x"],
                baseline_placeholder["bbox"]["x"],
                rel_tol=0.0,
                abs_tol=1,
            ) or not math.isclose(
                current_placeholder["bbox"]["y"],
                baseline_placeholder["bbox"]["y"],
                rel_tol=0.0,
                abs_tol=1,
            ) or not math.isclose(
                current_placeholder["bbox"]["width"],
                baseline_placeholder["bbox"]["width"],
                rel_tol=0.0,
                abs_tol=1,
            ) or not math.isclose(
                current_placeholder["bbox"]["height"],
                baseline_placeholder["bbox"]["height"],
                rel_tol=0.0,
                abs_tol=1,
            ):
                placeholders_changed.append(
                    {
                        "layout_id": layout_id,
                        "name": name,
                        "field": "bbox",
                    }
                )

    baseline_template_id = (
        baseline_records[0]["template_id"] if "template_id" in baseline_records[0] else None
    )

    return {
        "baseline_template_id": baseline_template_id,
        "target_template_id": target_template_id,
        "layouts_added": layouts_added,
        "layouts_removed": layouts_removed,
        "placeholders_changed": placeholders_changed,
        "issues": issues,
    }
