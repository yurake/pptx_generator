"""LayoutValidationSuite の実装。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from time import perf_counter
from typing import Any

from ...pipeline.template_extractor import (
    TemplateExtractor,
    TemplateExtractorOptions,
)
from ...utils.layout_metadata import summarize_placeholders
from .comparison import compare_with_analyzer_snapshot
from .constants import SUITE_VERSION
from .diff import build_diff_report
from .io import write_jsonl
from .records import (
    build_blueprint_lookup,
    build_heuristic_usage_result,
    collect_placeholder_records,
    detect_duplicate_placeholder_warnings,
    derive_media_hint,
    derive_text_hint,
)
from .template_ai import TemplateAIManager
from .types import LayoutValidationError, LayoutValidationOptions, LayoutValidationResult
from .utils import derive_template_id, resolve_layout_id
from .validators import validate_diff_report, validate_diagnostics, validate_records

logger = logging.getLogger(__name__)


class LayoutValidationSuite:
    """テンプレートレイアウト検証のエントリポイント。"""

    def __init__(self, options: LayoutValidationOptions) -> None:
        self.options = options
        self._template_ai = TemplateAIManager(options)

    def run(self) -> LayoutValidationResult:
        """検証を実行し成果物を生成する。"""

        if not self.options.template_path.exists():
            msg = f"テンプレートファイルが存在しません: {self.options.template_path}"
            raise LayoutValidationError(msg)

        self._template_ai.reset_run()

        start = perf_counter()
        extractor = TemplateExtractor(
            TemplateExtractorOptions(template_path=self.options.template_path)
        )
        template_spec = extractor.extract()
        template_id = self.options.template_id or derive_template_id(
            self.options.template_path
        )

        records, warnings, errors = self._build_layout_records(template_spec, template_id)

        analyzer_snapshot_issues: list[dict[str, Any]] = []
        snapshot_warnings, snapshot_errors, snapshot_issues = compare_with_analyzer_snapshot(
            records=records,
            template_id=template_id,
            snapshot_path=self.options.analyzer_snapshot_path,
        )
        warnings.extend(snapshot_warnings)
        errors.extend(snapshot_errors)
        analyzer_snapshot_issues.extend(snapshot_issues)

        extraction_time_ms = int((perf_counter() - start) * 1000)
        ai_stats = self._template_ai.stats()
        stats = {
            "layouts_total": len(records),
            "placeholders_total": sum(
                len(record["placeholders"]) for record in records
            ),
            "extraction_time_ms": extraction_time_ms,
            "template_ai_invoked": ai_stats.get("invoked", 0),
            "template_ai_success": ai_stats.get("success", 0),
            "template_ai_fallback": ai_stats.get("fallback", 0),
            "template_ai_failed": ai_stats.get("failed", 0),
        }

        diagnostics = {
            "template_id": template_id,
            "warnings": warnings,
            "errors": errors,
            "stats": stats,
            "template_ai": self._template_ai.layouts(),
        }

        validate_records(records)
        validate_diagnostics(diagnostics)

        output_dir = self.options.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        layouts_path = output_dir / "layouts.jsonl"
        diagnostics_path = output_dir / "diagnostics.json"
        write_jsonl(records, layouts_path)
        diagnostics_path.write_text(
            json.dumps(diagnostics, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        diff_report_path: Path | None = None
        diff_report: dict[str, Any] | None = None
        if self.options.baseline_path is not None:
            diff_report = build_diff_report(
                records=records,
                target_template_id=template_id,
                baseline_path=self.options.baseline_path,
            )
            if diff_report is not None:
                validate_diff_report(diff_report)
                if analyzer_snapshot_issues:
                    diff_report.setdefault("issues", []).extend(analyzer_snapshot_issues)
                diff_report_path = output_dir / "diff_report.json"
                diff_report_path.write_text(
                    json.dumps(diff_report, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
        elif analyzer_snapshot_issues:
            diff_report = {
                "baseline_template_id": "__analyzer_snapshot__",
                "target_template_id": template_id,
                "layouts_added": [],
                "layouts_removed": [],
                "placeholders_changed": [],
                "issues": analyzer_snapshot_issues,
            }
            validate_diff_report(diff_report)
            diff_report_path = output_dir / "diff_report.json"
            diff_report_path.write_text(
                json.dumps(diff_report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        return LayoutValidationResult(
            layouts_path=layouts_path,
            diagnostics_path=diagnostics_path,
            diff_report_path=diff_report_path,
            record_count=len(records),
            warnings_count=len(warnings),
            errors_count=len(errors),
        )

    # ------------------------------------------------------------------ #
    # レコード構築
    # ------------------------------------------------------------------ #
    def _build_layout_records(
        self,
        template_spec,
        template_id: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        records: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        seen_layout_ids: dict[str, int] = {}
        blueprint_lookup = build_blueprint_lookup(template_spec.blueprint)
        static_rules_payload = self._template_ai.policy_static_rules()

        for layout in template_spec.layouts:
            layout_id = resolve_layout_id(layout, seen_layout_ids)
            if layout.error:
                errors.append(
                    {
                        "code": "layout_extract_error",
                        "layout_id": layout_id,
                        "name": layout.name,
                        "detail": layout.error,
                    }
                )
            placeholder_records, placeholder_names, placeholder_warnings, placeholder_errors = collect_placeholder_records(
                layout=layout,
                layout_id=layout_id,
            )
            warnings.extend(placeholder_warnings)
            errors.extend(placeholder_errors)
            warnings.extend(
                detect_duplicate_placeholder_warnings(
                    layout_id=layout_id,
                    placeholder_names=placeholder_names,
                )
            )

            text_hint = derive_text_hint(placeholder_records)
            media_hint = derive_media_hint(placeholder_records)
            placeholder_summary = layout.placeholder_summary or summarize_placeholders(placeholder_records)

            heuristic_result = build_heuristic_usage_result(layout, placeholder_records)
            raw_usage_tags = set(heuristic_result.tags)
            base_meta_reasons = list(dict.fromkeys(heuristic_result.reasons))
            meta_payload_for_ai = self._template_ai.build_meta_payload(
                layout=layout,
                base_meta_reasons=base_meta_reasons,
            )
            blueprint_info = blueprint_lookup.get(layout.name)

            (
                raw_usage_tags,
                ai_result,
                ai_error,
                ai_warnings,
                ai_errors,
            ) = self._template_ai.apply(
                template_id=template_id,
                layout_id=layout_id,
                layout=layout,
                placeholder_records=placeholder_records,
                text_hint=text_hint,
                media_hint=media_hint,
                heuristic_tags=heuristic_result.tags,
                placeholder_summary=placeholder_summary,
                blueprint_info=blueprint_info,
                meta_payload=meta_payload_for_ai,
            )
            warnings.extend(ai_warnings)
            errors.extend(ai_errors)

            usage_tags, usage_tag_warnings = self._template_ai.normalize_usage_tags(
                layout_id=layout_id,
                layout_name=layout.name,
                raw_usage_tags=raw_usage_tags,
                heuristic_result=heuristic_result,
                ai_result=ai_result,
                ai_error=ai_error,
            )
            warnings.extend(usage_tag_warnings)

            meta_reasons: list[str] = list(base_meta_reasons)
            if ai_result is None or not ai_result.success:
                meta_reasons.append("template_ai:fallback")
            elif ai_result.source == "static":
                meta_reasons.append("template_ai:static")

            record_entry: dict[str, Any] = {
                "template_id": template_id,
                "layout_id": layout_id,
                "layout_name": layout.name,
                "placeholders": placeholder_records,
                "usage_tags": usage_tags,
                "text_hint": text_hint,
                "media_hint": media_hint,
                "placeholder_summary": placeholder_summary,
                "heuristic": {
                    "tags": sorted(heuristic_result.tags),
                    "reasons": heuristic_result.reasons,
                    "has_title_placeholder": heuristic_result.has_title_placeholder,
                    "has_body_placeholder": heuristic_result.has_body_placeholder,
                    "title_from_name": heuristic_result.title_from_name,
                },
                "static_rules": static_rules_payload,
                "version": SUITE_VERSION,
            }
            if blueprint_info:
                record_entry["blueprint"] = blueprint_info

            meta_entry: dict[str, Any] = {}
            if layout.layout_description:
                meta_entry["layout_description"] = layout.layout_description
            deduped_meta_reasons = list(dict.fromkeys(meta_reasons))
            if deduped_meta_reasons:
                meta_entry["heuristic_reason"] = "; ".join(deduped_meta_reasons)
            if meta_entry:
                record_entry["meta"] = meta_entry

            records.append(record_entry)

        for message in template_spec.warnings:
            warnings.append(
                {
                    "code": "extractor_warning",
                    "layout_id": "__template__",
                    "name": str(self.options.template_path.name),
                    "detail": message,
                }
            )

        for message in template_spec.errors:
            errors.append(
                {
                    "code": "extractor_error",
                    "layout_id": "__template__",
                    "name": str(self.options.template_path.name),
                    "detail": message,
                }
            )

        return records, warnings, errors

    # ------------------------------------------------------------------ #
    # 互換用ヘルパー
    # ------------------------------------------------------------------ #
    def _build_diff_report(
        self,
        *,
        records: list[dict[str, Any]],
        target_template_id: str,
        baseline_path: Path,
    ) -> dict[str, Any] | None:
        return build_diff_report(
            records=records,
            target_template_id=target_template_id,
            baseline_path=baseline_path,
        )
