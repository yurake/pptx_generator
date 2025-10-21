"""レンダリング監査と Analyzer 出力を突合し監視レポートを生成するステップ。"""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .base import PipelineContext

logger = logging.getLogger(__name__)

SEVERITY_ORDER = ("critical", "error", "warning", "info")


@dataclass(slots=True)
class MonitoringIntegrationOptions:
    """監視レポート生成に関する設定。"""

    enabled: bool = True
    output_filename: str = "monitoring_report.json"


class MonitoringIntegrationStep:
    """レンダリング監査と Analyzer 結果を統合した監視レポートを生成する。"""

    name = "monitoring_integration"

    def __init__(self, options: MonitoringIntegrationOptions | None = None) -> None:
        self.options = options or MonitoringIntegrationOptions()

    def run(self, context: PipelineContext) -> None:
        try:
            if not self.options.enabled:
                logger.debug("Monitoring integration is disabled")
                return

            rendering_log = self._load_rendering_log(context)
            if rendering_log is None:
                logger.warning("Monitoring integration skipped: rendering_log is missing")
                return

            analysis_after = self._load_analysis(context, "analysis_path")
            if analysis_after is None:
                logger.warning("Monitoring integration skipped: analysis_path is missing")
                return

            analysis_before = self._load_analysis(context, "analysis_pre_polisher_path")

            report = self._build_report(context, rendering_log, analysis_after, analysis_before)
            output_path = self._write_report(report, context.workdir)

            context.add_artifact("monitoring_report", report)
            context.add_artifact("monitoring_report_path", output_path)
            summary = self._build_summary(report)
            context.add_artifact("monitoring_summary", summary)

            alert_level = summary.get("alert_level")
            if alert_level in {"critical", "error"}:
                logger.error("Monitoring alerts detected: %s", summary.get("headline"))
            elif alert_level == "warning":
                logger.warning("Monitoring alerts detected: %s", summary.get("headline"))
            else:
                logger.info("Monitoring report generated without alerts")

            logger.info("Monitoring report generated: %s", output_path)
        finally:
            self._cleanup_pdf_only(context)

    def _load_rendering_log(self, context: PipelineContext) -> dict[str, Any] | None:
        raw = context.artifacts.get("rendering_log")
        if isinstance(raw, dict):
            return raw
        path_value = context.artifacts.get("rendering_log_path")
        return self._read_json(path_value)

    def _load_analysis(
        self, context: PipelineContext, artifact_key: str
    ) -> dict[str, Any] | None:
        path_value = context.artifacts.get(artifact_key)
        if path_value is None:
            return None
        return self._read_json(path_value)

    def _read_json(self, path_value: object | None) -> dict[str, Any] | None:
        if path_value is None:
            return None
        path = Path(str(path_value))
        if not path.exists():
            logger.warning("JSON ファイルが見つかりません: %s", path)
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.error("JSON 読み込みに失敗しました: %s (%s)", path, exc)
        return None

    def _build_report(
        self,
        context: PipelineContext,
        rendering_log: dict[str, Any],
        analysis_after: dict[str, Any],
        analysis_before: dict[str, Any] | None,
    ) -> dict[str, Any]:
        spec = context.spec
        rendering_slides = {
            entry.get("page_no"): entry
            for entry in rendering_log.get("slides", [])
            if isinstance(entry, dict)
        }

        issues_after = list(self._iter_issues(analysis_after))
        issues_before = list(self._iter_issues(analysis_before)) if analysis_before else []
        grouping_after = self._group_by_slide(issues_after)
        grouping_before = self._group_by_slide(issues_before)

        rendering_meta = rendering_log.get("meta") or {}
        polisher_meta = context.artifacts.get("polisher_metadata")
        pdf_meta = context.artifacts.get("pdf_export_metadata")

        alerts: list[dict[str, Any]] = []
        for index, slide_spec in enumerate(spec.slides, start=1):
            render_entry = rendering_slides.get(index, {})
            warnings = [
                warning
                for warning in render_entry.get("warnings", [])
                if isinstance(warning, dict)
            ]
            after_issues = grouping_after.get(slide_spec.id, [])
            before_issues = grouping_before.get(slide_spec.id, [])
            if not warnings and not after_issues:
                continue
            alerts.append(
                {
                    "slide_id": slide_spec.id,
                    "page_no": index,
                    "layout_id": slide_spec.layout,
                    "rendering_warning_count": len(warnings),
                    "rendering_warnings": warnings,
                    "analyzer_issue_count": len(after_issues),
                    "analyzer_issues": [
                        {
                            "id": issue.get("id"),
                            "type": issue.get("type"),
                            "severity": issue.get("severity"),
                            "message": issue.get("message"),
                        }
                        for issue in after_issues
                    ],
                    "resolved_issues": self._resolved_issue_ids(before_issues, after_issues),
                }
            )

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "spec_meta": spec.meta.model_dump(),
            "slides": len(spec.slides),
            "artifacts": {
                "analysis_before": self._artifact_str(context.artifacts.get("analysis_pre_polisher_path")),
                "analysis_after": self._artifact_str(context.artifacts.get("analysis_path")),
                "rendering_log": self._artifact_str(context.artifacts.get("rendering_log_path")),
            },
            "rendering": {
                "warnings_total": rendering_meta.get("warnings_total", 0),
                "empty_placeholders": rendering_meta.get("empty_placeholders", 0),
            },
            "analyzer": {
                "before_polisher": self._summarize_issues(issues_before) if issues_before else None,
                "after_pipeline": self._summarize_issues(issues_after),
                "improvement": self._calculate_improvement(issues_before, issues_after),
            },
            "alerts": alerts,
            "pipeline": {
                "polisher": polisher_meta,
                "pdf_export": pdf_meta,
            },
        }
        return report

    def _write_report(self, payload: dict[str, Any], workdir: Path) -> Path:
        workdir.mkdir(parents=True, exist_ok=True)
        output_path = workdir / self.options.output_filename
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path

    def _cleanup_pdf_only(self, context: PipelineContext) -> None:
        cleanup_target = context.artifacts.pop("pdf_cleanup_pptx_path", None)
        if not cleanup_target:
            return
        try:
            pptx_path = Path(str(cleanup_target))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to resolve PDF cleanup path: %s (%s)", cleanup_target, exc)
            context.artifacts.pop("pptx_path", None)
            return
        pptx_path.unlink(missing_ok=True)
        context.artifacts.pop("pptx_path", None)
        logger.info("Removed PPTX after PDF-only export: %s", pptx_path)

    def _build_summary(self, report: dict[str, Any]) -> dict[str, Any]:
        analyzer_after = report.get("analyzer", {}).get("after_pipeline") or {}
        total_issues = analyzer_after.get("total", 0)
        rendering_warnings = report.get("rendering", {}).get("warnings_total", 0)
        alerts = report.get("alerts", [])

        max_severity = self._maximum_severity(report.get("alerts", []))
        if alerts and max_severity in {"critical", "error"}:
            alert_level = "critical"
        elif alerts and (rendering_warnings > 0 or total_issues > 0):
            alert_level = "warning"
        else:
            alert_level = "ok"

        headline = f"{len(alerts)} slides require attention" if alerts else "No outstanding monitoring alerts"
        summary = {
            "alert_level": alert_level,
            "headline": headline,
            "rendering_warnings": rendering_warnings,
            "analyzer_issues": total_issues,
            "alerts": [
                {
                    "slide_id": entry.get("slide_id"),
                    "rendering_warning_count": entry.get("rendering_warning_count", 0),
                    "analyzer_issue_count": entry.get("analyzer_issue_count", 0),
                }
                for entry in alerts[:5]
            ],
        }
        return summary

    def _maximum_severity(self, alerts: Iterable[dict[str, Any]]) -> str | None:
        severity_rank = {name: index for index, name in enumerate(SEVERITY_ORDER)}
        max_rank = None
        max_severity = None
        for entry in alerts:
            for issue in entry.get("analyzer_issues", []):
                severity = issue.get("severity")
                rank = severity_rank.get(severity, len(SEVERITY_ORDER))
                if max_rank is None or rank < max_rank:
                    max_rank = rank
                    max_severity = severity
        return max_severity

    def _summarize_issues(self, issues: list[dict[str, Any]]) -> dict[str, Any]:
        severity_counter: Counter[str] = Counter()
        type_counter: Counter[str] = Counter()
        for issue in issues:
            severity_counter[issue.get("severity", "unknown")] += 1
            type_counter[issue.get("type", "unknown")] += 1
        return {
            "total": len(issues),
            "by_severity": dict(sorted(severity_counter.items(), key=self._sort_severity)),
            "by_type": dict(sorted(type_counter.items())),
        }

    def _calculate_improvement(
        self,
        issues_before: list[dict[str, Any]],
        issues_after: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not issues_before:
            return None
        before_ids = {issue.get("id") for issue in issues_before}
        after_ids = {issue.get("id") for issue in issues_after}
        resolved = [issue_id for issue_id in before_ids if issue_id and issue_id not in after_ids]
        return {
            "resolved": len(resolved),
            "delta": len(issues_after) - len(issues_before),
            "resolved_issue_ids": sorted(resolved),
        }

    def _iter_issues(self, payload: dict[str, Any] | None) -> Iterable[dict[str, Any]]:
        if not payload:
            return []
        issues = payload.get("issues", [])
        return [issue for issue in issues if isinstance(issue, dict)]

    def _group_by_slide(
        self, issues: Iterable[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for issue in issues:
            target = issue.get("target") or {}
            slide_id = target.get("slide_id")
            if slide_id:
                grouped[slide_id].append(issue)
        return grouped

    def _resolved_issue_ids(
        self,
        issues_before: Iterable[dict[str, Any]],
        issues_after: Iterable[dict[str, Any]],
    ) -> list[str]:
        before_ids = {issue.get("id") for issue in issues_before if issue.get("id")}
        after_ids = {issue.get("id") for issue in issues_after if issue.get("id")}
        resolved = sorted(before_ids - after_ids)
        return resolved

    @staticmethod
    def _artifact_str(value: object | None) -> str | None:
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _sort_severity(item: tuple[str, int]) -> tuple[int, str]:
        severity, _ = item
        try:
            index = SEVERITY_ORDER.index(severity)
        except ValueError:
            index = len(SEVERITY_ORDER)
        return (index, severity)
