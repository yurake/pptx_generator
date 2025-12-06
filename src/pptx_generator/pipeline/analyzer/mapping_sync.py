from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any

from ...models import (
    MappingLog,
    MappingLogAnalyzerIssue,
    MappingLogAnalyzerSummary,
)

logger = logging.getLogger(__name__)


def sync_mapping_log(context, analysis: dict[str, Any]) -> None:
    mapping_log_ref = context.artifacts.get("mapping_log_path")
    if mapping_log_ref is None:
        return
    try:
        mapping_log_path = Path(str(mapping_log_ref))
    except Exception:  # noqa: BLE001
        return
    if not mapping_log_path.exists():
        return
    try:
        mapping_log = MappingLog.model_validate_json(mapping_log_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "mapping_log.json の読み込みに失敗したため Analyzer 連携をスキップします: %s",
            exc,
        )
        return

    issues_payload = analysis.get("issues")
    if not isinstance(issues_payload, list):
        return

    overall_by_type: Counter[str] = Counter()
    overall_by_severity: Counter[str] = Counter()
    for slide in mapping_log.slides:
        slide_issues = [
            issue
            for issue in issues_payload
            if isinstance(issue, dict) and _target_slide_id(issue) == slide.ref_id
        ]
        summary = build_analyzer_summary(slide_issues)
        slide.analyzer = summary
        overall_by_type.update(summary.issue_counts_by_type)
        overall_by_severity.update(summary.issue_counts_by_severity)

    mapping_log.meta.analyzer_issue_count = sum(overall_by_type.values())
    mapping_log.meta.analyzer_issue_counts_by_type = dict(overall_by_type)
    mapping_log.meta.analyzer_issue_counts_by_severity = dict(overall_by_severity)

    mapping_log_path.write_text(
        json.dumps(mapping_log.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    context.add_artifact("mapping_log", mapping_log)


def _target_slide_id(issue: dict[str, Any]) -> str | None:
    target = issue.get("target")
    if not isinstance(target, dict):
        return None
    slide_id = target.get("slide_id")
    if isinstance(slide_id, str) and slide_id:
        return slide_id
    return None


def build_analyzer_summary(issues_payload: list[dict[str, Any]]) -> MappingLogAnalyzerSummary:
    type_counter: Counter[str] = Counter()
    severity_counter: Counter[str] = Counter()
    summary_issues: list[MappingLogAnalyzerIssue] = []

    for issue in issues_payload:
        if not isinstance(issue, dict):
            continue

        issue_id = str(issue.get("id") or "")
        issue_type = str(issue.get("type") or "")
        severity = str(issue.get("severity") or "")
        message = str(issue.get("message") or "")

        target = issue.get("target")
        if not isinstance(target, dict):
            target = {}
        metrics = issue.get("metrics")
        if not isinstance(metrics, dict):
            metrics = {}

        fix = issue.get("fix")
        fix_type: str | None = None
        fix_payload: dict[str, Any] | None = None
        if isinstance(fix, dict):
            fix_type_value = fix.get("type")
            if isinstance(fix_type_value, str):
                fix_type = fix_type_value
            payload_value = fix.get("payload")
            if isinstance(payload_value, dict):
                fix_payload = payload_value

        summary_issues.append(
            MappingLogAnalyzerIssue(
                issue_id=issue_id,
                issue_type=issue_type,
                severity=severity,
                message=message,
                target=target,
                metrics=metrics,
                fix_type=fix_type,
                fix_payload=fix_payload,
            )
        )
        type_counter[issue_type] += 1
        severity_counter[severity] += 1

    return MappingLogAnalyzerSummary(
        issue_count=sum(type_counter.values()),
        issue_counts_by_type=dict(type_counter),
        issue_counts_by_severity=dict(severity_counter),
        issues=summary_issues,
    )
