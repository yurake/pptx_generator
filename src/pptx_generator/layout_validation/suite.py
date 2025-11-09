"""テンプレート構造の検証スイート本体。"""

from __future__ import annotations

import json
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
from .schema import (
    DIAGNOSTICS_VALIDATOR,
    DIFF_REPORT_VALIDATOR,
    LAYOUT_RECORD_VALIDATOR,
)

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

    def run(self) -> LayoutValidationResult:
        """検証を実行し成果物を生成する。"""

        if not self.options.template_path.exists():
            msg = f"テンプレートファイルが存在しません: {self.options.template_path}"
            raise LayoutValidationError(msg)

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
        diagnostics = {
            "template_id": template_id,
            "warnings": warnings,
            "errors": errors,
            "stats": {
                "layouts_total": len(records),
                "placeholders_total": sum(
                    len(record["placeholders"]) for record in records
                ),
                "extraction_time_ms": extraction_time_ms,
            },
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

                placeholder_records.append(
                    {
                        "name": shape.name,
                        "type": normalised_type,
                        "bbox": bbox,
                        "style_hint": style_hint,
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

            (
                raw_usage_tags,
                has_title_placeholder,
                has_body_placeholder,
                title_from_name,
            ) = self._derive_usage_tags(layout, placeholder_records)

            usage_tags_tuple, unknown_tags = normalize_usage_tags_with_unknown(raw_usage_tags)
            usage_tags_set = set(usage_tags_tuple)

            title_conflict_removed = False
            if "title" in usage_tags_set and has_body_placeholder and not title_from_name:
                usage_tags_set.discard("title")
                title_conflict_removed = True

            if not usage_tags_set:
                usage_tags_set.add("generic")

            usage_tags = sorted(usage_tags_set)

            if unknown_tags:
                warnings.append(
                    {
                        "code": "usage_tag_unknown",
                        "layout_id": layout_id,
                        "name": layout.name,
                        "detail": ", ".join(sorted(unknown_tags)),
                    }
                )

            if title_conflict_removed:
                detail = "タイトルタグが本文プレースホルダーの存在により除外されました"
                if not title_from_name:
                    detail += "（名前ベースの判定外）"
                warnings.append(
                    {
                        "code": "usage_tag_title_suppressed",
                        "layout_id": layout_id,
                        "name": layout.name,
                        "detail": detail,
                    }
                )
            text_hint = self._derive_text_hint(placeholder_records)
            media_hint = self._derive_media_hint(placeholder_records)

            records.append(
                {
                    "template_id": template_id,
                    "layout_id": layout_id,
                    "layout_name": layout.name,
                    "placeholders": placeholder_records,
                    "usage_tags": usage_tags,
                    "text_hint": text_hint,
                    "media_hint": media_hint,
                    "version": SUITE_VERSION,
                }
            )

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
        key = (shape.placeholder_type or "").upper()
        if key in PLACEHOLDER_TYPE_ALIASES:
            return PLACEHOLDER_TYPE_ALIASES[key]
        # name から推測
        guessed = self._guess_type_from_name(shape.name)
        return guessed or "unknown"

    @staticmethod
    def _guess_type_from_name(name: str | None) -> str | None:
        if not name:
            return None
        lowered = name.casefold()
        if "title" in lowered:
            return "title"
        if "sub" in lowered:
            return "subtitle"
        if "note" in lowered:
            return "notes"
        if "table" in lowered:
            return "table"
        if "chart" in lowered or "graph" in lowered:
            return "chart"
        if "image" in lowered or "picture" in lowered or "photo" in lowered:
            return "image"
        if "body" in lowered or "content" in lowered:
            return "body"
        return None

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

    @staticmethod
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
