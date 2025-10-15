"""テンプレートリリースメタ生成と差分検証ロジック。"""

from __future__ import annotations

import hashlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from ..models import (
    TemplateRelease,
    TemplateReleaseChanges,
    TemplateReleaseDiagnostics,
    TemplateReleaseGoldenRun,
    TemplateReleaseLayoutDetail,
    TemplateReleaseLayoutDiff,
    TemplateReleaseLayouts,
    TemplateReleaseReport,
    TemplateSpec,
)


def build_template_release(
    *,
    template_path: Path,
    spec: TemplateSpec,
    template_id: str,
    brand: str,
    version: str,
    generated_by: str | None = None,
    reviewed_by: str | None = None,
    golden_runs: list[TemplateReleaseGoldenRun] | None = None,
    extra_warnings: Iterable[str] | None = None,
    extra_errors: Iterable[str] | None = None,
) -> TemplateRelease:
    """TemplateSpec からテンプレリリースメタを生成する。"""

    template_hash = _compute_sha256(template_path)

    details: list[TemplateReleaseLayoutDetail] = []
    warnings: list[str] = []
    errors: list[str] = []

    for layout in spec.layouts:
        layout_issues: list[str] = []

        anchor_names: list[str] = []
        placeholder_names: list[str] = []
        anchor_counter: Counter[str] = Counter()

        if layout.error:
            _append_unique(errors, f"layout {layout.name}: {layout.error}")

        for shape in layout.anchors:
            anchor_names.append(shape.name)
            anchor_counter.update([shape.name])

            if shape.is_placeholder:
                placeholder_names.append(shape.name)

            if shape.error:
                message = f"layout {layout.name} / shape {shape.name}: {shape.error}"
                _append_unique(errors, message)
                _append_unique(layout_issues, f"error: {shape.error}")

            if shape.missing_fields:
                missing = ", ".join(shape.missing_fields)
                message = f"layout {layout.name} / shape {shape.name}: missing fields -> {missing}"
                _append_unique(warnings, message)
                _append_unique(layout_issues, f"missing_fields: {missing}")

            if shape.conflict:
                message = f"layout {layout.name} / shape {shape.name}: {shape.conflict}"
                _append_unique(warnings, message)
                _append_unique(layout_issues, f"conflict: {shape.conflict}")

        duplicate_anchor_names = [
            name for name, count in anchor_counter.items() if count > 1
        ]
        if duplicate_anchor_names:
            message = (
                f"layout {layout.name}: duplicate anchors -> {', '.join(duplicate_anchor_names)}"
            )
            _append_unique(warnings, message)

        detail = TemplateReleaseLayoutDetail(
            name=layout.name,
            anchor_count=len(anchor_names),
            placeholder_count=len(placeholder_names),
            anchor_names=anchor_names,
            placeholder_names=placeholder_names,
            duplicate_anchor_names=duplicate_anchor_names,
            issues=layout_issues,
        )
        details.append(detail)

    for message in spec.warnings:
        _append_unique(warnings, f"extractor: {message}")

    for message in spec.errors:
        _append_unique(errors, f"extractor: {message}")

    if extra_warnings:
        for message in extra_warnings:
            _append_unique(warnings, message)

    if extra_errors:
        for message in extra_errors:
            _append_unique(errors, message)

    total_layouts = len(details)
    if total_layouts:
        placeholder_total = sum(detail.placeholder_count for detail in details)
        placeholders_avg = round(placeholder_total / total_layouts, 2)
    else:
        placeholders_avg = 0.0

    layouts = TemplateReleaseLayouts(
        total=total_layouts,
        placeholders_avg=placeholders_avg,
        details=details,
    )

    diagnostics = TemplateReleaseDiagnostics(warnings=warnings, errors=errors)

    release = TemplateRelease(
        template_id=template_id,
        brand=brand,
        version=version,
        template_path=str(template_path),
        hash=template_hash,
        generated_at=datetime.now(timezone.utc).isoformat(),
        generated_by=generated_by,
        reviewed_by=reviewed_by,
        extractor={
            "extracted_at": spec.extracted_at,
            "source_template": spec.template_path,
        },
        layouts=layouts,
        diagnostics=diagnostics,
        golden_runs=golden_runs or [],
    )
    return release


def load_template_release(path: Path) -> TemplateRelease:
    """保存済みのテンプレートリリースメタを読み込む。"""

    content = path.read_text(encoding="utf-8")
    return TemplateRelease.model_validate_json(content)


def build_release_report(
    *,
    current: TemplateRelease,
    baseline: TemplateRelease | None = None,
) -> TemplateReleaseReport:
    """テンプレートリリース差分レポートを生成する。"""

    current_details = {detail.name: detail for detail in current.layouts.details}
    baseline_details = (
        {detail.name: detail for detail in baseline.layouts.details}
        if baseline is not None
        else {}
    )

    layouts_added = sorted(
        name for name in current_details.keys() if name not in baseline_details
    )
    layouts_removed = sorted(
        name for name in baseline_details.keys() if name not in current_details
    )

    intersecting = sorted(set(current_details.keys()) & set(baseline_details.keys()))
    layout_diffs: list[TemplateReleaseLayoutDiff] = []
    for name in intersecting:
        current_detail = current_details[name]
        baseline_detail = baseline_details[name]

        anchors_added = sorted(
            _diff(current_detail.anchor_names, baseline_detail.anchor_names)
        )
        anchors_removed = sorted(
            _diff(baseline_detail.anchor_names, current_detail.anchor_names)
        )
        placeholders_added = sorted(
            _diff(current_detail.placeholder_names, baseline_detail.placeholder_names)
        )
        placeholders_removed = sorted(
            _diff(baseline_detail.placeholder_names, current_detail.placeholder_names)
        )

        if (
            anchors_added
            or anchors_removed
            or placeholders_added
            or placeholders_removed
            or current_detail.duplicate_anchor_names
        ):
            layout_diffs.append(
                TemplateReleaseLayoutDiff(
                    name=name,
                    anchors_added=anchors_added,
                    anchors_removed=anchors_removed,
                    placeholders_added=placeholders_added,
                    placeholders_removed=placeholders_removed,
                    duplicate_anchor_names=current_detail.duplicate_anchor_names,
                )
            )

    changes = TemplateReleaseChanges(
        layouts_added=layouts_added,
        layouts_removed=layouts_removed,
        layout_diffs=layout_diffs,
    )

    report = TemplateReleaseReport(
        template_id=current.template_id,
        baseline_id=baseline.template_id if baseline is not None else None,
        generated_at=datetime.now(timezone.utc).isoformat(),
        hashes={
            "current": current.hash,
            "baseline": baseline.hash if baseline is not None else None,
        },
        changes=changes,
        diagnostics=current.diagnostics,
    )
    return report


def _compute_sha256(template_path: Path) -> str:
    hasher = hashlib.sha256()
    with template_path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(8192), b""):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"


def _append_unique(target: list[str], message: str) -> None:
    if message not in target:
        target.append(message)


def _diff(current: Iterable[str], baseline: Iterable[str]) -> list[str]:
    """baseline に存在せず current に追加された要素を抽出する。"""

    current_set = set(current)
    baseline_set = set(baseline)
    return list(current_set - baseline_set)
