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

from ..models import LayoutInfo, ShapeInfo, TemplateSpec
from ..utils.usage_tags import normalize_usage_tags_with_unknown
from ..pipeline.template_extractor import TemplateExtractor, TemplateExtractorOptions
from ..template_ai import TemplateAIOptions, TemplateAIResult, TemplateAIService
from ..template_ai.client import TemplateAIClientConfigurationError
from ..template_ai.policy import TemplateAIPolicyError
from .schema import (
    DIAGNOSTICS_VALIDATOR,
    DIFF_REPORT_VALIDATOR,
    LAYOUT_RECORD_VALIDATOR,
)

logger = logging.getLogger(__name__)

EMU_PER_INCH = 914400
SUITE_VERSION = "1.0.0"


PLACEHOLDER_TYPE_ALIASES: dict[str, str] = {
    "BODY": "body",
    "VERTICAL_BODY": "body",
    "TITLE": "title",
    "SUBTITLE": "subtitle",
    "CENTER_TITLE": "title",
    "TABLE": "table",
    "CHART": "chart",
    "PICTURE": "image",
    "CONTENT": "body",
    "TEXT": "body",
    "MEDIA_CLIP": "media",
    "OBJECT": "object",
    "FOOTER": "footer",
    "SLIDE_NUMBER": "footer",
    "DATE": "footer",
    "VERTICAL_TITLE": "title",
    "NOTES": "notes",
}

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
    template_ai_policy_path: Path | None = Path("config/template_ai_policies.json")
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
        self._template_ai_layouts: list[dict[str, str | list[str] | None]] = []
        self._initialize_template_ai()

    def _initialize_template_ai(self) -> None:
        if self.options.disable_template_ai:
            logger.info("template AI is disabled by option")
            return
        policy_path = self.options.template_ai_policy_path
        if policy_path is None or not policy_path.exists():
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
    ) -> TemplateAIResult | None:
        service = self._template_ai_service
        if service is None:
            return None

        self._template_ai_stats["invoked"] += 1
        started = perf_counter()
        try:
            result = service.classify_layout(
                template_id=template_id,
                layout_id=layout_id,
                layout_name=layout_name,
                placeholders=placeholders,
                text_hint=text_hint,
                media_hint=media_hint,
                heuristic_usage_tags=heuristic_usage_tags,
            )
        finally:
            elapsed = perf_counter() - started
            should_log = elapsed > 0.5 or logger.isEnabledFor(logging.DEBUG)
            if should_log:
                logger.info(
                    "template AI classify: layout=%s provider=%s elapsed=%.3fs",
                    layout_id,
                    result.source if result else "-",
                    elapsed,
                )

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
                "usage_tags": list(result.usage_tags or ()),
                "unknown_tags": list(result.unknown_tags),
            }
        )
        return result

    def _build_layout_records(
        self,
        template_spec: TemplateSpec,
        template_id: str,
        baseline_spec: TemplateSpec | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        diagnostics: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        layout_records: list[dict[str, Any]] = []
        seen_layout_ids: dict[str, int] = {}
        self._template_ai_stats = {"invoked": 0, "success": 0, "fallback": 0, "failed": 0}
        self._template_ai_layouts.clear()

        for layout in template_spec.layouts:
            layout_id = self._resolve_layout_id(layout, seen_layout_ids)
            record = self._build_layout_record(
                template_id=template_id,
                layout=layout,
                layout_id=layout_id,
                warnings=warnings,
                errors=errors,
            )
            layout_records.append(record)

        if baseline_spec:
            diff_report = self._build_diff_report(layout_records, baseline_spec)
        else:
            diff_report = None

        diagnostics_path = self.options.output_dir / "diagnostics.json"
        layouts_path = self.options.output_dir / "layouts.jsonl"
        diff_report_path = self.options.output_dir / "diff_report.json" if diff_report else None

        self._write_jsonl(layout_records, layouts_path)
        diagnostics_payload = {
            "template_id": template_id,
            "version": SUITE_VERSION,
            "generated_at": template_spec.extracted_at,
            "records": layout_records,
            "template_ai": {
                **self._template_ai_stats,
                "layouts": self._template_ai_layouts,
            },
            "warnings": warnings,
            "errors": errors,
        }
        diagnostics_path.write_text(json.dumps(diagnostics_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        if diff_report and diff_report_path:
            diff_report_path.write_text(
                json.dumps(diff_report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        return layout_records, warnings, errors

    def _build_layout_record(
        self,
        *,
        template_id: str,
        layout: LayoutInfo,
        layout_id: str,
        warnings: list[dict[str, Any]],
        errors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        placeholders = self._map_placeholders(layout.anchors)
        placeholder_records = self._build_placeholder_records(placeholders, layout)

        text_hint = self._derive_text_hint(placeholder_records)
        media_hint = self._derive_media_hint(placeholder_records)

        (
            heuristic_tags,
            has_title_placeholder,
            has_body_placeholder,
            title_from_name,
        ) = self._derive_usage_tags(layout, placeholder_records)

        ai_result = self._invoke_template_ai(
            template_id=template_id,
            layout_id=layout_id,
            layout_name=layout.name or layout_id,
            placeholders=placeholder_records,
            text_hint=text_hint,
            media_hint=media_hint,
            heuristic_usage_tags=sorted(heuristic_tags),
        )

        if ai_result and ai_result.success and ai_result.usage_tags:
            raw_usage_tags = set(ai_result.usage_tags)
            if ai_result.source == "static":
                # static フォールバックの場合はヒューリスティックの結果も保持してタグ欠落を防ぐ
                raw_usage_tags.update(heuristic_tags)
        else:
            raw_usage_tags = set(heuristic_tags)
            if ai_result:
                if ai_result.error:
                    warnings.append(
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

        if not usage_tags_set:
            usage_tags_set.add("generic")

        usage_tags = sorted(usage_tags_set)

        if ai_result and ai_result.unknown_tags:
            warnings.append(
                {
                    "code": "usage_tag_ai_unknown",
                    "layout_id": layout_id,
                    "name": layout.name,
                    "detail": ", ".join(ai_result.unknown_tags),
                }
            )

        record = {
            "template_id": template_id,
            "layout_id": layout_id,
            "layout_name": layout.name,
            "placeholders": placeholder_records,
            "usage_tags": usage_tags,
            "title_conflict_removed": title_conflict_removed,
            "unknown_usage_tags": sorted(unknown_tags),
            "text_hint": text_hint,
            "media_hint": media_hint,
        }

        LAYOUT_RECORD_VALIDATOR.validate(record)

        return record

    def _map_placeholders(self, anchors: Iterable[ShapeInfo]) -> list[dict[str, Any]]:
        mapped: list[dict[str, Any]] = []
        for anchor in anchors:
            if not anchor.is_placeholder:
                continue

            placeholder_type = PLACEHOLDER_TYPE_ALIASES.get(anchor.placeholder_type, anchor.placeholder_type.casefold())

            mapped.append(
                {
                    "name": anchor.name,
                    "type": placeholder_type,
                    "bbox": {
                        "x": int(anchor.left_in * EMU_PER_INCH),
                        "y": int(anchor.top_in * EMU_PER_INCH),
                        "width": int(anchor.width_in * EMU_PER_INCH),
                        "height": int(anchor.height_in * EMU_PER_INCH),
                    },
                    "style_hint": {
                        "sample_text": anchor.text,
                    },
                    "flags": [],
                }
            )

        return mapped

    def _build_placeholder_records(
        self,
        placeholders: Iterable[dict[str, Any]],
        layout: LayoutInfo,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        placeholder_names: list[str] = []

        for placeholder in placeholders:
            placeholder_names.append(placeholder.get("name") or "")
            normalised_type = (placeholder.get("type") or "").casefold()

            flags: list[str] = []
            if normalised_type in TEXT_PLACEHOLDER_TYPES:
                text = (placeholder.get("style_hint") or {}).get("sample_text") or ""
                if text:
                    level_count = text.count("\n") + 1
                    if level_count > 5:
                        flags.append("overflow")
                        warnings.append(
                            {
                                "code": "placeholder_text_overflow",
                                "layout_id": layout.identifier or layout.name,
                                "name": placeholder.get("name"),
                                "detail": f"{level_count} levels",
                            }
                        )
            records.append(
                {
                    "name": placeholder.get("name"),
                    "type": normalised_type,
                    "bbox": placeholder.get("bbox"),
                    "style_hint": placeholder.get("style_hint"),
                    "flags": flags,
                }
            )

        return records

    def _derive_text_hint(self, placeholders: Iterable[dict[str, Any]]) -> dict[str, Any]:
        body_placeholders = [placeholder for placeholder in placeholders if (placeholder.get("type") or "").casefold() in TEXT_PLACEHOLDER_TYPES]
        if not body_placeholders:
            return {"max_chars": 0, "max_lines": 0}

        max_lines = max(
            ((placeholder.get("style_hint") or {}).get("sample_text") or "").count("\n") + 1
            for placeholder in body_placeholders
        )
        max_chars = max(len((placeholder.get("style_hint") or {}).get("sample_text") or "") for placeholder in body_placeholders)

        return {"max_chars": max_chars, "max_lines": max_lines}

    def _derive_media_hint(self, placeholders: Iterable[dict[str, Any]]) -> dict[str, Any]:
        has_table_placeholder = any((placeholder.get("type") or "").casefold() == "table" for placeholder in placeholders)
        has_chart_placeholder = any((placeholder.get("type") or "").casefold() == "chart" for placeholder in placeholders)
        has_image_placeholder = any((placeholder.get("type") or "").casefold() in IMAGE_PLACEHOLDER_TYPES for placeholder in placeholders)

        return {
            "allow_table": has_table_placeholder,
            "allow_chart": has_chart_placeholder,
            "allow_image": has_image_placeholder,
        }

    def _derive_usage_tags(
        layout: LayoutInfo, placeholders: Iterable[dict[str, Any]]
    ) -> tuple[set[str], bool, bool, bool]:
        tags: set[str] = set()
        name = layout.name or ""
        name_cf = name.casefold()

        has_title_placeholder = False
        has_body_placeholder = False
        has_chart_placeholder = False
        has_table_placeholder = False
        has_image_placeholder = False

        for placeholder in placeholders:
            p_type_raw = placeholder.get("type") or ""
            p_type = p_type_raw.casefold()
            placeholder_name_cf = (placeholder.get("name") or "").casefold()

            if p_type == "title":
                has_title_placeholder = True
            elif p_type in {"body", "content", "text"}:
                has_body_placeholder = True
                tags.add("content")
            elif p_type == "chart":
                has_chart_placeholder = True
                tags.add("chart")
            elif p_type == "table":
                has_table_placeholder = True
                tags.add("table")
            elif p_type == "image":
                has_image_placeholder = True
                tags.add("visual")
            elif p_type == "object":
                if any(keyword in placeholder_name_cf for keyword in ("body", "content", "text", "message")):
                    has_body_placeholder = True
                    tags.add("content")
                elif any(keyword in placeholder_name_cf for keyword in ("logo", "image", "picture", "visual")):
                    has_image_placeholder = True
                    tags.add("visual")
            elif p_type == "media":
                if any(keyword in placeholder_name_cf for keyword in ("image", "picture", "photo", "visual")):
                    has_image_placeholder = True
                    tags.add("visual")

        if has_chart_placeholder and "chart" not in tags:
            tags.add("chart")
        if has_table_placeholder and "table" not in tags:
            tags.add("table")
        if has_image_placeholder and "visual" not in tags:
            tags.add("visual")

        if "agenda" in name_cf or "toc" in name_cf:
            tags.add("agenda")
        if "summary" in name_cf or "overview" in name_cf:
            tags.add("overview")
        if "table" in name_cf:
            tags.add("table")
        if "chart" in name_cf:
            tags.add("chart")

        title_from_name = LayoutValidationSuite._looks_like_title_layout(name, name_cf)
        if title_from_name:
            tags.add("title")
        elif has_title_placeholder and not has_body_placeholder:
            tags.add("title")

        if has_body_placeholder:
            tags.add("content")

        return tags, has_title_placeholder, has_body_placeholder, title_from_name

    @staticmethod
    def _looks_like_title_layout(name: str, name_cf: str) -> bool:
        if not name:
            return False

        # ASCII keywords
        if any(keyword in name_cf for keyword in ("cover", "front page")):
            return True
        if "title" in name_cf and "content" not in name_cf:
            return True

        # Japanese keywords（casefold では変わらないためそのまま検索）
        if "タイトル" in name and "コンテンツ" not in name:
            return True
        if "表紙" in name:
            return True
        if "セクション" in name and ("タイトル" in name or "表紙" in name):
            return True

        return False

    @staticmethod
    def _derive_text_hint(self, placeholders: Iterable[dict[str, Any]]) -> dict[str, Any]:
        body_placeholders = [placeholder for placeholder in placeholders if (placeholder.get("type") or "").casefold() in TEXT_PLACEHOLDER_TYPES]
        if not body_placeholders:
            return {"max_chars": 0, "max_lines": 0}

        max_lines = max(
            ((placeholder.get("style_hint") or {}).get("sample_text") or "").count("\n") + 1
            for placeholder in body_placeholders
        )
        max_chars = max(len((placeholder.get("style_hint") or {}).get("sample_text") or "") for placeholder in body_placeholders)

        return {"max_chars": max_chars, "max_lines": max_lines}

    def _derive_media_hint(self, placeholders: Iterable[dict[str, Any]]) -> dict[str, Any]:
        has_table_placeholder = any((placeholder.get("type") or "").casefold() == "table" for placeholder in placeholders)
        has_chart_placeholder = any((placeholder.get("type") or "").casefold() == "chart" for placeholder in placeholders)
        has_image_placeholder = any((placeholder.get("type") or "").casefold() in IMAGE_PLACEHOLDER_TYPES for placeholder in placeholders)

        return {
            "allow_table": has_table_placeholder,
            "allow_chart": has_chart_placeholder,
            "allow_image": has_image_placeholder,
        }

    def _build_diff_report(
        self,
        current_records: list[dict[str, Any]],
        baseline_spec: TemplateSpec,
    ) -> dict[str, Any]:
        baseline_records = [self._build_layout_record(
            template_id=baseline_spec.template_path,
            layout=layout,
            layout_id=layout.identifier or layout.name,
            warnings=[],
            errors=[],
        ) for layout in baseline_spec.layouts]

        baseline_map = {record["layout_id"]: record for record in baseline_records}
        current_map = {record["layout_id"]: record for record in current_records}

        layouts_added = sorted(set(current_map) - set(baseline_map))
        layouts_removed = sorted(set(baseline_map) - set(current_map))

        placeholders_changed: list[dict[str, Any]] = []
        issues: list[dict[str, Any]] = []

        for layout_id, current in current_map.items():
            if layout_id not in baseline_map:
                continue

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
            "target_template_id": template_id,
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
