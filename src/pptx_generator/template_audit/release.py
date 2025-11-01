"""テンプレートリリースメタ生成と差分検証ロジック。"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import logging

from ..models import (
    TemplateRelease,
    TemplateReleaseAnalyzerFixSummary,
    TemplateReleaseAnalyzerIssueSummary,
    TemplateReleaseAnalyzerMetrics,
    TemplateReleaseAnalyzerReport,
    TemplateReleaseAnalyzerRunMetrics,
    TemplateReleaseAnalyzerSummary,
    TemplateReleaseAnalyzerSummaryDelta,
    TemplateReleaseChanges,
    TemplateReleaseDiagnostics,
    TemplateReleaseEnvironment,
    TemplateReleaseGoldenRun,
    TemplateReleaseLayoutDetail,
    TemplateReleaseLayoutDiff,
    TemplateReleaseLayouts,
    TemplateReleaseReport,
    TemplateReleaseSummary,
    TemplateReleaseSummaryDelta,
    TemplateSpec,
)
from .environment import collect_environment_info


logger = logging.getLogger(__name__)


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

    analyzer_metrics, analyzer_warnings = _collect_analyzer_metrics(golden_runs or [])
    for message in analyzer_warnings:
        _append_unique(warnings, message)

    environment, environment_warnings = collect_environment_info()
    for message in environment_warnings:
        _append_unique(warnings, message)

    total_layouts = len(details)
    anchor_total = sum(len(detail.anchor_names) for detail in details)
    if total_layouts:
        placeholder_total = sum(detail.placeholder_count for detail in details)
        placeholders_avg = round(placeholder_total / total_layouts, 2)
    else:
        placeholders_avg = 0.0
        placeholder_total = 0

    layouts = TemplateReleaseLayouts(
        total=total_layouts,
        placeholders_avg=placeholders_avg,
        details=details,
    )

    diagnostics = TemplateReleaseDiagnostics(warnings=warnings, errors=errors)

    summary = TemplateReleaseSummary(
        layouts=total_layouts,
        anchors=anchor_total,
        placeholders=placeholder_total,
        warning_count=len(warnings),
        error_count=len(errors),
        analyzer_issue_total=(
            analyzer_metrics.summary.issues.total
            if analyzer_metrics is not None
            else None
        ),
        analyzer_fix_total=(
            analyzer_metrics.summary.fixes.total
            if analyzer_metrics is not None
            else None
        ),
    )

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
        analyzer_metrics=analyzer_metrics,
        golden_runs=golden_runs or [],
        summary=summary,
        environment=environment,
    )
    return release


def load_template_release(path: Path) -> TemplateRelease:
    """保存済みのテンプレートリリースメタを読み込む。"""

    logger.info("Loading template release from %s", path.resolve())
    content = path.read_text(encoding="utf-8")
    release = TemplateRelease.model_validate_json(content)
    logger.info("Loaded template release from %s", path.resolve())
    return release


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

    analyzer_report = None
    if current.analyzer_metrics is not None:
        current_summary = current.analyzer_metrics.summary
        baseline_summary = (
            baseline.analyzer_metrics.summary
            if baseline is not None and baseline.analyzer_metrics is not None
            else None
        )
        delta = (
            _compute_analyzer_delta(current_summary, baseline_summary)
            if baseline_summary is not None
            else None
        )
        analyzer_report = TemplateReleaseAnalyzerReport(
            current=current_summary,
            baseline=baseline_summary,
            delta=delta,
        )

    summary_delta = None
    if baseline is not None:
        summary_delta = _compute_summary_delta(
            current.summary,
            baseline.summary if baseline is not None else None,
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
        analyzer=analyzer_report,
        summary=current.summary,
        summary_baseline=baseline.summary if baseline is not None else None,
        summary_delta=summary_delta,
    )
    return report


def _collect_analyzer_metrics(
    golden_runs: list[TemplateReleaseGoldenRun],
) -> tuple[TemplateReleaseAnalyzerMetrics | None, list[str]]:
    if not golden_runs:
        return None, []

    warnings: list[str] = []
    run_metrics: list[TemplateReleaseAnalyzerRunMetrics] = []
    summary_issues_by_type: dict[str, int] = {}
    summary_issues_by_severity: dict[str, int] = {}
    summary_fixes_by_type: dict[str, int] = {}
    total_issues = 0
    total_fixes = 0
    included_runs = 0

    for run in golden_runs:
        spec_path = run.spec_path

        if run.status != "passed":
            warnings.append(
                f"golden spec {spec_path}: status={run.status} のため Analyzer メトリクスを集計しませんでした"
            )
            run_metrics.append(
                TemplateReleaseAnalyzerRunMetrics(
                    spec_path=spec_path,
                    status="skipped",
                    issues=TemplateReleaseAnalyzerIssueSummary(),
                    fixes=TemplateReleaseAnalyzerFixSummary(),
                )
            )
            continue

        analysis_path = run.analysis_path
        if not analysis_path:
            warnings.append(
                f"golden spec {spec_path}: analysis.json が存在しないため Analyzer メトリクスを集計しませんでした"
            )
            run_metrics.append(
                TemplateReleaseAnalyzerRunMetrics(
                    spec_path=spec_path,
                    status="skipped",
                    issues=TemplateReleaseAnalyzerIssueSummary(),
                    fixes=TemplateReleaseAnalyzerFixSummary(),
                )
            )
            continue

        file_path = Path(analysis_path)
        if not file_path.exists():
            warnings.append(
                f"golden spec {spec_path}: analysis.json が見つからないため Analyzer メトリクスを集計しませんでした"
            )
            run_metrics.append(
                TemplateReleaseAnalyzerRunMetrics(
                    spec_path=spec_path,
                    status="skipped",
                    issues=TemplateReleaseAnalyzerIssueSummary(),
                    fixes=TemplateReleaseAnalyzerFixSummary(),
                )
            )
            continue

        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:  # pragma: no cover - 異常系
            warnings.append(
                f"golden spec {spec_path}: analysis.json の読み込みに失敗しました ({exc})"
            )
            run_metrics.append(
                TemplateReleaseAnalyzerRunMetrics(
                    spec_path=spec_path,
                    status="skipped",
                    issues=TemplateReleaseAnalyzerIssueSummary(),
                    fixes=TemplateReleaseAnalyzerFixSummary(),
                )
            )
            continue

        issues_payload = payload.get("issues") or []
        fixes_payload = payload.get("fixes") or []

        issue_summary = _summarize_issues(issues_payload)
        fix_summary = _summarize_fixes(fixes_payload)

        included_runs += 1
        total_issues += issue_summary.total
        total_fixes += fix_summary.total
        _merge_counts(summary_issues_by_type, issue_summary.by_type)
        _merge_counts(summary_issues_by_severity, issue_summary.by_severity)
        _merge_counts(summary_fixes_by_type, fix_summary.by_type)

        run_metrics.append(
            TemplateReleaseAnalyzerRunMetrics(
                spec_path=spec_path,
                status="included",
                issues=issue_summary,
                fixes=fix_summary,
            )
        )

    aggregated_at = datetime.now(timezone.utc).isoformat()
    summary = TemplateReleaseAnalyzerSummary(
        run_count=included_runs,
        issues=TemplateReleaseAnalyzerIssueSummary(
            total=total_issues,
            by_type=_sorted_dict(summary_issues_by_type),
            by_severity=_sorted_dict(summary_issues_by_severity),
        ),
        fixes=TemplateReleaseAnalyzerFixSummary(
            total=total_fixes,
            by_type=_sorted_dict(summary_fixes_by_type),
        ),
    )

    metrics = TemplateReleaseAnalyzerMetrics(
        aggregated_at=aggregated_at,
        runs=run_metrics,
        summary=summary,
    )
    return metrics, warnings


def _summarize_issues(payload: list[dict[str, object]]) -> TemplateReleaseAnalyzerIssueSummary:
    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}

    for item in payload:
        issue_type = str(item.get("type") or "unknown")
        severity = str(item.get("severity") or "unknown")
        _increment(by_type, issue_type)
        _increment(by_severity, severity)

    return TemplateReleaseAnalyzerIssueSummary(
        total=len(payload),
        by_type=_sorted_dict(by_type),
        by_severity=_sorted_dict(by_severity),
    )


def _summarize_fixes(payload: list[dict[str, object]]) -> TemplateReleaseAnalyzerFixSummary:
    by_type: dict[str, int] = {}

    for item in payload:
        fix_type = str(item.get("type") or "unknown")
        _increment(by_type, fix_type)

    return TemplateReleaseAnalyzerFixSummary(
        total=len(payload),
        by_type=_sorted_dict(by_type),
    )


def _increment(target: dict[str, int], key: str) -> None:
    target[key] = target.get(key, 0) + 1


def _merge_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for key, value in source.items():
        target[key] = target.get(key, 0) + value


def _sorted_dict(source: dict[str, int]) -> dict[str, int]:
    return dict(sorted(source.items()))


def _compute_analyzer_delta(
    current: TemplateReleaseAnalyzerSummary,
    baseline: TemplateReleaseAnalyzerSummary,
) -> TemplateReleaseAnalyzerSummaryDelta:
    issue_delta = _subtract_counts(current.issues.by_type, baseline.issues.by_type)
    severity_delta = _subtract_counts(
        current.issues.by_severity, baseline.issues.by_severity
    )
    fix_delta = _subtract_counts(current.fixes.by_type, baseline.fixes.by_type)
    return TemplateReleaseAnalyzerSummaryDelta(
        issues=_sorted_dict(issue_delta),
        severity=_sorted_dict(severity_delta),
        fixes=_sorted_dict(fix_delta),
        total_issue_change=current.issues.total - baseline.issues.total,
        total_fix_change=current.fixes.total - baseline.fixes.total,
    )


def _subtract_counts(
    current: dict[str, int], baseline: dict[str, int]
) -> dict[str, int]:
    keys = set(current.keys()) | set(baseline.keys())
    return {key: current.get(key, 0) - baseline.get(key, 0) for key in keys}


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


def _compute_summary_delta(
    current: TemplateReleaseSummary,
    baseline: TemplateReleaseSummary | None,
) -> TemplateReleaseSummaryDelta | None:
    if baseline is None:
        return None

    def _diff_optional(curr: int | None, base: int | None) -> int | None:
        if curr is None and base is None:
            return None
        return (curr or 0) - (base or 0)

    return TemplateReleaseSummaryDelta(
        layouts=current.layouts - baseline.layouts,
        anchors=current.anchors - baseline.anchors,
        placeholders=current.placeholders - baseline.placeholders,
        warning_count=current.warning_count - baseline.warning_count,
        error_count=current.error_count - baseline.error_count,
        analyzer_issue_total=_diff_optional(
            current.analyzer_issue_total, baseline.analyzer_issue_total
        ),
        analyzer_fix_total=_diff_optional(
            current.analyzer_fix_total, baseline.analyzer_fix_total
        ),
    )
