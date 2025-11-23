"""テンプレート構造の検証スイート本体。"""

from __future__ import annotations

import json
import logging
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Iterable

from ..models import LayoutInfo, ShapeInfo, TemplateBlueprint, TemplateSpec
from ..utils.usage_tags import normalize_usage_tags_with_unknown
from ..pipeline.template_extractor import TemplateExtractor, TemplateExtractorOptions
from ..template_ai import TemplateAIOptions, TemplateAIResult, TemplateAIService
from ..template_ai.client import TemplateAIClientConfigurationError
from ..template_ai.policy import TemplateAIPolicyError
from ..utils.layout_metadata import (
    HeuristicUsageTagsResult,
    derive_usage_tags,
    normalise_placeholder_type,
    summarize_placeholders,
)
from .schema import (
    DIAGNOSTICS_VALIDATOR,
    DIFF_REPORT_VALIDATOR,
    LAYOUT_RECORD_VALIDATOR,
)

EMU_PER_INCH = 914400
SUITE_VERSION = "1.1.0"

logger = logging.getLogger(__name__)


TEXT_PLACEHOLDER_TYPES = {"body", "title", "subtitle", "notes"}
IMAGE_PLACEHOLDER_TYPES = {"image", "media", "object"}


@dataclass(slots=True)
class LayoutValidationOptions:
    """レイアウト検証処理のオプション。"""

    template_path: Path
    output_dir: Path
    template_id: str | None = None
    baseline_path: Path | None = None
    analyzer_snapshot_path: Path | None = None
    template_ai_policy_path: Path | None = None
    template_ai_policy_id: str | None = None
    disable_template_ai: bool = False


@dataclass(slots=True)
class LayoutValidationResult:
    """検証処理の結果。"""

    layouts_path: Path
    diagnostics_path: Path
    diff_report_path: Path | None
    record_count: int
    warnings_count: int
    errors_count: int


class LayoutValidationError(RuntimeError):
    """レイアウト検証に関する例外。"""


class LayoutValidationSuite:
    """テンプレートレイアウト検証のエントリポイント。"""

    def __init__(self, options: LayoutValidationOptions) -> None:
        self.options = options
        self._template_ai_service: TemplateAIService | None = None
        self._template_ai_stats = {
            "invoked": 0,
            "success": 0,
            "fallback": 0,
            "failed": 0,
        }
        self._template_ai_layouts: list[dict[str, Any]] = []
        self._initialize_template_ai()

    def _initialize_template_ai(self) -> None:
        if self.options.disable_template_ai:
            logger.info("template AI is disabled by option")
            return
        policy_path = self.options.template_ai_policy_path
        if policy_path is None:
            return
        try:
            service = TemplateAIService(
                TemplateAIOptions(
                    policy_path=policy_path,
                    policy_id=self.options.template_ai_policy_id,
                )
            )
        except (TemplateAIPolicyError, TemplateAIClientConfigurationError) as exc:
            logger.warning("テンプレートAIの初期化に失敗しました: %s", exc)
            return
        self._template_ai_service = service

    def _invoke_template_ai(
        self,
        *,
        template_id: str,
        layout_id: str,
        layout_name: str,
        placeholders: list[dict[str, Any]],
        text_hint: dict[str, Any],
        media_hint: dict[str, Any],
        heuristic_usage_tags: list[str],
        placeholder_summary: dict[str, Any],
        blueprint: dict[str, Any] | None,
        meta: dict[str, Any] | None,
    ) -> TemplateAIResult | None:
        service = self._template_ai_service
        if service is None:
            return None

        self._template_ai_stats = {key: self._template_ai_stats.get(key, 0) for key in ("invoked", "success", "fallback", "failed")}
        self._template_ai_stats["invoked"] += 1
        started = perf_counter()
        result: TemplateAIResult | None = None
        try:
            result = service.classify_layout(
                template_id=template_id,
                layout_id=layout_id,
                layout_name=layout_name,
                placeholders=placeholders,
                text_hint=text_hint,
                media_hint=media_hint,
                heuristic_usage_tags=heuristic_usage_tags,
                placeholder_summary=placeholder_summary,
                blueprint=blueprint,
                meta=meta,
            )
        except TypeError:
            # 古い実装との互換性のため、追加メタデータをサポートしないクライアントには従来の引数のみで再呼び出しする。
            result = service.classify_layout(
                template_id=template_id,
                layout_id=layout_id,
                layout_name=layout_name,
                placeholders=placeholders,
                text_hint=text_hint,
                media_hint=media_hint,
                heuristic_usage_tags=heuristic_usage_tags,
            )
        except TemplateAIClientConfigurationError as exc:
            logger.warning("template AI classify failed: %s", exc)
            self._template_ai_stats["failed"] += 1
            self._template_ai_layouts.append(
                {
                    "layout_id": layout_id,
                    "layout_name": layout_name,
                    "source": "error",
                    "reason": None,
                    "tags": [],
                    "unknown_tags": [],
                    "error": str(exc),
                }
            )
            return None
        finally:
            elapsed = perf_counter() - started
            if logger.isEnabledFor(logging.DEBUG) or elapsed > 0.5:
                source = getattr(result, "source", "-") if result else "-"
                logger.info(
                    "template AI classify: layout=%s provider=%s elapsed=%.3fs",
                    layout_id,
                    source,
                    elapsed,
                )

        if result is None:
            return None

        if result.success:
            self._template_ai_stats["success"] += 1
        elif result.source == "static":
            self._template_ai_stats["fallback"] += 1
        else:
            self._template_ai_stats["failed"] += 1

        self._template_ai_layouts.append(
            {
                "layout_id": layout_id,
                "layout_name": layout_name,
                "source": result.source,
                "reason": result.reason,
                "tags": list(result.usage_tags or ()),
                "unknown_tags": list(result.unknown_tags),
                "error": result.error,
            }
        )

        return result

    def run(self) -> LayoutValidationResult:
        """検証を実行し成果物を生成する。"""

        if not self.options.template_path.exists():
            msg = f"テンプレートファイルが存在しません: {self.options.template_path}"
            raise LayoutValidationError(msg)

        self._template_ai_stats = {
            "invoked": 0,
            "success": 0,
            "fallback": 0,
            "failed": 0,
        }
        self._template_ai_layouts = []

        start = perf_counter()
        extractor = TemplateExtractor(
            TemplateExtractorOptions(template_path=self.options.template_path)
        )
        template_spec = extractor.extract()
        template_id = self.options.template_id or self._derive_template_id(
            self.options.template_path
        )

        records, warnings, errors = self._build_layout_records(template_spec, template_id)

        analyzer_snapshot_issues: list[dict[str, Any]] = []
        if self.options.analyzer_snapshot_path is not None:
            snapshot_warnings, snapshot_errors, snapshot_issues = (
                self._compare_with_analyzer_snapshot(records, template_id)
            )
            warnings.extend(snapshot_warnings)
            errors.extend(snapshot_errors)
            analyzer_snapshot_issues.extend(snapshot_issues)

        extraction_time_ms = int((perf_counter() - start) * 1000)
        stats = {
            "layouts_total": len(records),
            "placeholders_total": sum(
                len(record["placeholders"]) for record in records
            ),
            "extraction_time_ms": extraction_time_ms,
        }
        stats.update(
            {
                "template_ai_invoked": self._template_ai_stats.get("invoked", 0),
                "template_ai_success": self._template_ai_stats.get("success", 0),
                "template_ai_fallback": self._template_ai_stats.get("fallback", 0),
                "template_ai_failed": self._template_ai_stats.get("failed", 0),
            }
        )

        diagnostics = {
            "template_id": template_id,
            "warnings": warnings,
            "errors": errors,
            "stats": stats,
            "template_ai": self._template_ai_layouts,
        }

        self._validate_records(records)
        self._validate_diagnostics(diagnostics)

        output_dir = self.options.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        layouts_path = output_dir / "layouts.jsonl"
        diagnostics_path = output_dir / "diagnostics.json"
        self._write_jsonl(records, layouts_path)
        diagnostics_path.write_text(
            json.dumps(diagnostics, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        diff_report_path: Path | None = None
        diff_report: dict[str, Any] | None = None
        if self.options.baseline_path is not None:
            diff_report = self._build_diff_report(
                records=records,
                target_template_id=template_id,
                baseline_path=self.options.baseline_path,
            )
            if diff_report is not None:
                self._validate_diff_report(diff_report)
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
            self._validate_diff_report(diff_report)
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

    # --- レコード生成とバリデーション -------------------------------------------------

    def _build_layout_records(
        self, template_spec: TemplateSpec, template_id: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        records: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        seen_layout_ids: dict[str, int] = {}
        blueprint_lookup = self._build_blueprint_lookup(template_spec.blueprint)
        static_rules_payload = self._policy_static_rules()

        for layout in template_spec.layouts:
            layout_id = self._resolve_layout_id(layout, seen_layout_ids)
            if layout.error:
                errors.append(
                    {
                        "code": "layout_extract_error",
                        "layout_id": layout_id,
                        "name": layout.name,
                        "detail": layout.error,
                    }
                )

            placeholder_records: list[dict[str, Any]] = []
            placeholder_names: list[str] = []

            for shape in layout.anchors:
                if not self._should_include_shape(shape):
                    continue

                normalised_type = self._normalise_placeholder_type(shape)
                bbox = self._shape_bbox(shape)
                style_hint = self._build_style_hint(shape)
                flags = self._build_flags(shape, normalised_type)

                if bbox["x"] < 0 or bbox["y"] < 0:
                    warnings.append(
                        {
                            "code": "placeholder_negative_origin",
                            "layout_id": layout_id,
                            "name": shape.name,
                            "detail": f"x={bbox['x']} y={bbox['y']}",
                        }
                    )

                placeholder_records.append(
                    {
                        "name": shape.name,
                        "type": normalised_type,
                        "bbox": bbox,
                        "style_hint": style_hint,
                        "shape_type": shape.shape_type,
                        "flags": flags,
                    }
                )
                placeholder_names.append(shape.name)

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

            duplicates = [
                name
                for name, count in Counter(placeholder_names).items()
                if count > 1
            ]
            for name in duplicates:
                warnings.append(
                    {
                        "code": "duplicate_placeholder",
                        "layout_id": layout_id,
                        "name": name,
                    }
                )

            text_hint = self._derive_text_hint(placeholder_records)
            media_hint = self._derive_media_hint(placeholder_records)

            placeholder_summary = (
                layout.placeholder_summary or summarize_placeholders(placeholder_records)
            )

            if layout.heuristic:
                heuristic_result = HeuristicUsageTagsResult(
                    tags=set(layout.heuristic.get("tags") or []),
                    has_title_placeholder=bool(layout.heuristic.get("has_title_placeholder")),
                    has_body_placeholder=bool(layout.heuristic.get("has_body_placeholder")),
                    title_from_name=bool(layout.heuristic.get("title_from_name")),
                    reasons=list(layout.heuristic.get("reasons") or []),
                )
            else:
                heuristic_result = derive_usage_tags(layout.name or "", placeholder_records)
            heuristic_tags = heuristic_result.tags
            has_title_placeholder = heuristic_result.has_title_placeholder
            has_body_placeholder = heuristic_result.has_body_placeholder
            title_from_name = heuristic_result.title_from_name

            raw_usage_tags = set(heuristic_tags)
            base_meta_reasons = list(dict.fromkeys(heuristic_result.reasons))
            meta_payload = (
                {"heuristic_reason": "; ".join(base_meta_reasons)} if base_meta_reasons else None
            )
            blueprint_info = blueprint_lookup.get(layout.name)
            ai_error = False

            ai_result = self._invoke_template_ai(
                template_id=template_id,
                layout_id=layout_id,
                layout_name=layout.name or layout_id,
                placeholders=placeholder_records,
                text_hint=text_hint,
                media_hint=media_hint,
                heuristic_usage_tags=sorted(heuristic_tags),
                placeholder_summary=placeholder_summary,
                blueprint=blueprint_info,
                meta=meta_payload,
            )

            if ai_result and ai_result.success and ai_result.usage_tags:
                raw_usage_tags = set(ai_result.usage_tags)
                if ai_result.source == "static":
                    raw_usage_tags.update(heuristic_tags)
            else:
                if ai_result:
                    if ai_result.error:
                        ai_error = True
                        raw_usage_tags = set()
                        errors.append(
                            {
                                "code": "usage_tag_ai_error",
                                "layout_id": layout_id,
                                "name": layout.name,
                                "detail": ai_result.error,
                            }
                        )
                    elif ai_result.source != "static":
                        warnings.append(
                            {
                                "code": "usage_tag_ai_fallback",
                                "layout_id": layout_id,
                                "name": layout.name,
                                "detail": "生成AIが使用できなかったためヒューリスティックへフォールバックしました",
                            }
                        )

            usage_tags_tuple, unknown_tags = normalize_usage_tags_with_unknown(raw_usage_tags)
            usage_tags_set = set(usage_tags_tuple)

            title_conflict_removed = False
            if "title" in usage_tags_set and has_body_placeholder and not title_from_name:
                usage_tags_set.discard("title")
                title_conflict_removed = True

            if ai_error:
                usage_tags = sorted(usage_tags_set)
            else:
                if not usage_tags_set:
                    usage_tags_set.add("generic")
                usage_tags = sorted(usage_tags_set)

            if ai_result and ai_result.success:
                if ai_result.unknown_tags:
                    warnings.append(
                        {
                            "code": "usage_tag_ai_unknown",
                            "layout_id": layout_id,
                            "name": layout.name,
                            "detail": ", ".join(ai_result.unknown_tags),
                        }
                    )
            elif unknown_tags:
                warnings.append(
                    {
                        "code": "usage_tag_unknown",
                        "layout_id": layout_id,
                        "name": layout.name,
                        "detail": ", ".join(sorted(unknown_tags)),
                    }
                )

            meta_reasons: list[str] = base_meta_reasons
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
                    "tags": sorted(heuristic_tags),
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
            if meta_reasons:
                record_entry["meta"] = {
                    "heuristic_reason": "; ".join(dict.fromkeys(meta_reasons))
                }

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

    @staticmethod
    def _should_include_shape(shape: ShapeInfo) -> bool:
        if shape.is_placeholder:
            return True
        if shape.placeholder_type:
            return True
        # SlideBullet などの汎用アンカーも保持する
        if shape.name and shape.name.lower() not in {"rectangle", "textbox"}:
            return True
        return False

    def _normalise_placeholder_type(self, shape: ShapeInfo) -> str:
        return normalise_placeholder_type(shape.placeholder_type, shape.name)

    @staticmethod
    def _shape_bbox(shape: ShapeInfo) -> dict[str, int]:
        return {
            "x": int(round(shape.left_in * EMU_PER_INCH)),
            "y": int(round(shape.top_in * EMU_PER_INCH)),
            "width": int(round(shape.width_in * EMU_PER_INCH)),
            "height": int(round(shape.height_in * EMU_PER_INCH)),
        }

    @staticmethod
    def _build_style_hint(shape: ShapeInfo) -> dict[str, Any]:
        style_hint: dict[str, Any] = {}
        if shape.text:
            style_hint["sample_text"] = shape.text[:120]
        if shape.conflict:
            style_hint["conflict"] = shape.conflict
        return style_hint

    @staticmethod
    def _build_flags(shape: ShapeInfo, placeholder_type: str) -> list[str]:
        flags: list[str] = []
        if placeholder_type == "unknown":
            flags.append("unknown_type")
        if shape.conflict:
            flags.append("anchor_conflict")
        if shape.missing_fields:
            flags.append("missing_fields")
        return flags

    @staticmethod
    def _build_blueprint_lookup(
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

    def _policy_static_rules(self) -> list[dict[str, Any]]:
        service = self._template_ai_service
        if service is None:
            return []
        policy = getattr(service, "_policy", None)
        if policy is None:
            return []
        payload: list[dict[str, Any]] = []
        for rule in policy.static_rules:
            payload.append(
                {
                    "layout_name_pattern": rule.layout_name_pattern,
                    "tags": list(rule.tags),
                }
            )
        return payload

    def _compare_with_analyzer_snapshot(
        self, records: list[dict[str, Any]], template_id: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        warnings: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        issues: list[dict[str, Any]] = []

        snapshot_path = self.options.analyzer_snapshot_path
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
                entry = {
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

    def _derive_text_hint(self, placeholders: Iterable[dict[str, Any]]) -> dict[str, int]:
        max_chars = 0
        max_lines = 0
        for placeholder in placeholders:
            p_type = placeholder.get("type")
            if p_type not in TEXT_PLACEHOLDER_TYPES:
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

    def _derive_media_hint(
        self, placeholders: Iterable[dict[str, Any]]
    ) -> dict[str, bool]:
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

    def _validate_records(self, records: list[dict[str, Any]]) -> None:
        errors: list[str] = []
        for index, record in enumerate(records):
            for err in LAYOUT_RECORD_VALIDATOR.iter_errors(record):
                path = ".".join(str(part) for part in err.path)
                errors.append(f"record[{index}].{path}: {err.message}")
        if errors:
            raise LayoutValidationError("layouts.jsonl のスキーマ検証に失敗しました\n" + "\n".join(errors))

    def _validate_diagnostics(self, diagnostics: dict[str, Any]) -> None:
        errors = [
            err.message
            for err in DIAGNOSTICS_VALIDATOR.iter_errors(diagnostics)
        ]
        if errors:
            raise LayoutValidationError(
                "diagnostics.json のスキーマ検証に失敗しました\n" + "\n".join(errors)
            )

    def _validate_diff_report(self, diff_report: dict[str, Any]) -> None:
        errors = [err.message for err in DIFF_REPORT_VALIDATOR.iter_errors(diff_report)]
        if errors:
            raise LayoutValidationError(
                "diff_report.json のスキーマ検証に失敗しました\n" + "\n".join(errors)
            )

    # --- 差分出力 ------------------------------------------------------------------

    def _build_diff_report(
        self,
        *,
        records: list[dict[str, Any]],
        target_template_id: str,
        baseline_path: Path,
    ) -> dict[str, Any] | None:
        if not baseline_path.exists():
            raise LayoutValidationError(f"ベースラインが存在しません: {baseline_path}")

        baseline_records = self._load_jsonl(baseline_path)
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

    # --- ファイルユーティリティ ----------------------------------------------------

    @staticmethod
    def _write_jsonl(records: Iterable[dict[str, Any]], path: Path) -> None:
        with path.open("w", encoding="utf-8") as file:
            for record in records:
                file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
                file.write("\n")

    @staticmethod
    def _load_jsonl(path: Path) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
        return records

    @staticmethod
    def _resolve_layout_id(layout: LayoutInfo, seen: dict[str, int]) -> str:
        if layout.identifier:
            base = f"id_{layout.identifier}"
        else:
            base = LayoutValidationSuite._slugify_layout_name(layout.name)
        if not base:
            base = "layout"
        count = seen.get(base, 0) + 1
        seen[base] = count
        if count == 1:
            return base
        return f"{base}__{count:02d}"

    @staticmethod
    def _slugify_layout_name(name: str) -> str:
        normalised = unicodedata.normalize("NFKC", name or "").strip()
        normalised = normalised.replace(" ", "_")
        normalised = re.sub(r"[\s/\\]+", "_", normalised)
        normalised = re.sub(r"[^0-9A-Za-z_\-一-龯ぁ-んァ-ンー]+", "", normalised)
        return normalised.lower()

    @staticmethod
    def _derive_template_id(path: Path) -> str:
        stem = unicodedata.normalize("NFKC", path.stem)
        stem = re.sub(r"[^0-9A-Za-z_\-一-龯ぁ-んァ-ンー]+", "", stem)
        return stem or "template"
