"""Implementation of the TemplateExtractor pipeline step."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from zipfile import BadZipFile

from ...pipeline.base import PipelineContext
from .anchor_validation import AnchorValidationMixin
from .blueprint import BlueprintBuilderMixin
from .errors import DuplicateAnchorError
from .helpers import slugify_layout_name
from .jobspec import JobSpecBuilderMixin
from .options import TemplateExtractorOptions
from .shape_processing import ShapeExtractionMixin
from ...utils.layout_metadata import (
    derive_usage_tags,
    generate_layout_description,
    summarize_placeholders,
)
from ...branding_extractor import BrandingExtractionError, extract_branding_config
from ...models import FontSpec, LayoutInfo, ShapeInfo, TemplateBlueprint, TemplateSpec

logger = logging.getLogger(__name__)

__all__ = ["TemplateExtractorStep"]


class TemplateExtractorStep(
    AnchorValidationMixin,
    BlueprintBuilderMixin,
    JobSpecBuilderMixin,
    ShapeExtractionMixin,
):
    """テンプレートファイルから図形情報を抽出するステップ。"""

    name = "TemplateExtractor"

    def __init__(self, options: TemplateExtractorOptions) -> None:
        self.options = options
        self._slide_width_emu: int | None = None
        self._slide_height_emu: int | None = None
        self._heading_font_default = FontSpec(
            name="Meiryo UI", size_pt=32.0, color_hex="#1A1A1A"
        )
        self._body_font_default = FontSpec(
            name="Meiryo UI", size_pt=18.0, color_hex="#333333"
        )
        self._template_source: Literal["slide", "template"] = "template"

    def run(self, context: PipelineContext) -> None:
        """テンプレート抽出を実行する。"""
        logger.info("テンプレート抽出を開始: %s", self.options.template_path)

        try:
            template_spec = self.extract_template_spec()
            output_path = self._determine_output_path(context)
            self._save_template_spec(template_spec, output_path)
            jobspec_scaffold = self.build_jobspec_scaffold(template_spec, output_path)
            jobspec_path = self._determine_jobspec_path(output_path)
            self._save_jobspec_scaffold(jobspec_scaffold, jobspec_path)

            context.add_artifact("template_spec", template_spec)
            context.add_artifact("template_spec_path", output_path)
            context.add_artifact("jobspec_scaffold", jobspec_scaffold)
            context.add_artifact("jobspec_path", jobspec_path)

            logger.info(
                "テンプレート抽出完了: %s (jobspec=%s)", output_path, jobspec_path
            )

        except Exception as exc:
            logger.error("テンプレート抽出に失敗: %s", exc)
            raise

    def extract_template_spec(self) -> TemplateSpec:
        """テンプレートファイルから仕様を抽出する。"""
        if not self.options.template_path.exists():
            raise FileNotFoundError(
                f"テンプレートファイルが見つかりません: {self.options.template_path}"
            )

        self._load_font_defaults()

        from . import Presentation

        try:
            presentation = Presentation(self.options.template_path)
        except Exception as exc:
            raise RuntimeError(
                f"テンプレートファイルの読み込みに失敗しました: {exc}"
            ) from exc

        try:
            slide_width = int(presentation.slide_width)
            slide_height = int(presentation.slide_height)
        except Exception as exc:  # noqa: BLE001
            logger.error("スライドサイズの取得に失敗しました: %s", exc)
            raise RuntimeError("スライドサイズの取得に失敗しました") from exc

        if slide_width <= 0 or slide_height <= 0:
            logger.error(
                "スライドサイズが不正です (width=%s, height=%s)",
                slide_width,
                slide_height,
            )
            raise RuntimeError(
                "スライドサイズが不正です。テンプレートのページ設定を確認してください。"
            )

        self._slide_width_emu = slide_width
        self._slide_height_emu = slide_height

        layout_mode = (self.options.layout_mode or "dynamic").lower()
        if layout_mode not in {"dynamic", "static"}:
            layout_mode = "dynamic"
        template_source: Literal["slide", "template"] = "template"
        if layout_mode == "static":
            candidate_source = (self.options.static_source or "slide").lower()
            template_source = "slide" if candidate_source == "slide" else "template"
        self._template_source = template_source
        layouts: list[LayoutInfo] = []
        warnings: list[str] = []
        errors: list[str] = []

        if template_source == "slide":
            containers = enumerate(presentation.slides, start=1)
        else:
            containers = enumerate(presentation.slide_layouts, start=1)

        for index, container in containers:
            try:
                layout_info = self._extract_layout_info(
                    container,
                    index=index,
                    source_mode=template_source,
                )

                if self.options.layout_filter and not self._matches_filter(
                    layout_info.name, self.options.layout_filter
                ):
                    continue

                layouts.append(layout_info)

            except DuplicateAnchorError:
                raise
            except RuntimeError as exc:
                container_name = getattr(container, "name", None) or f"index={index}"
                error_msg = f"レイアウト '{container_name}' の抽出に失敗: {exc}"
                logger.warning(error_msg)
                errors.append(error_msg)
            except Exception as exc:
                container_name = getattr(container, "name", None) or f"index={index}"
                error_msg = f"レイアウト '{container_name}' の抽出に失敗: {exc}"
                logger.warning(error_msg)
                errors.append(error_msg)

        blueprint: TemplateBlueprint | None = None
        if layout_mode == "static":
            blueprint = self._build_blueprint(layouts)

        return TemplateSpec(
            template_path=str(self.options.template_path),
            extracted_at=datetime.now(timezone.utc).isoformat(),
            template_source=template_source,
            layouts=layouts,
            warnings=warnings,
            errors=errors,
            layout_mode=layout_mode,  # type: ignore[arg-type]
            blueprint=blueprint,
        )

    def _extract_layout_info(
        self,
        container,
        *,
        index: int,
        source_mode: Literal["slide", "template"],
    ) -> LayoutInfo:
        prototype_index: int | None = None
        if source_mode == "slide":
            base_name = getattr(container, "name", None)
            if not base_name:
                slide_layout = getattr(container, "slide_layout", None)
                base_name = (
                    getattr(slide_layout, "name", None)
                    if slide_layout is not None
                    else None
                )
            slugified = slugify_layout_name(base_name)
            if slugified:
                layout_name = f"{slugified}-{index:02d}"
            else:
                layout_name = f"slide-{index:02d}"
            identifier = None
            try:
                slide_identifier = getattr(container, "slide_id", None)
            except Exception:  # noqa: BLE001
                slide_identifier = None
            if slide_identifier is not None:
                identifier = str(slide_identifier)
            prototype_index = index
            shapes_iterable = getattr(container, "shapes", ())
        else:
            layout_name = getattr(container, "name", None)
            identifier = None
            try:
                layout_identifier = getattr(container, "slide_layout_id", None)
            except Exception:  # noqa: BLE001
                layout_identifier = None
            if layout_identifier is not None:
                identifier = str(layout_identifier)
            shapes_iterable = getattr(container, "shapes", ())
            if not layout_name:
                layout_name = f"layout-{index:02d}"
        anchors: list[ShapeInfo] = []

        for shape in shapes_iterable:
            try:
                shape_info = self._extract_shape_info(shape)

                if self.options.anchor_filter and not self._matches_filter(
                    shape_info.name, self.options.anchor_filter
                ):
                    continue

                anchors.append(shape_info)

            except Exception as exc:
                error_msg = (
                    f"図形 '{getattr(shape, 'name', '不明な図形')}' の抽出エラー: {exc}"
                )
                logger.warning(error_msg)

                error_shape = ShapeInfo(
                    name=getattr(shape, "name", "不明な図形"),
                    shape_type="unknown",
                    left_in=0.0,
                    top_in=0.0,
                    width_in=0.0,
                    height_in=0.0,
                    error=error_msg,
                )
                anchors.append(error_shape)

        self._check_duplicate_anchors(anchors, layout_name, index, source_mode)

        placeholder_records = [
            self._build_placeholder_record(shape_info)
            for shape_info in anchors
            if self._should_include_for_summary(shape_info)
        ]
        placeholder_summary = summarize_placeholders(placeholder_records)
        heuristic_result = derive_usage_tags(layout_name or "", placeholder_records)
        heuristic_payload = {
            "tags": sorted(heuristic_result.tags),
            "reasons": heuristic_result.reasons,
            "has_title_placeholder": heuristic_result.has_title_placeholder,
            "has_body_placeholder": heuristic_result.has_body_placeholder,
            "title_from_name": heuristic_result.title_from_name,
        }
        if (
            not heuristic_payload["tags"]
            and not heuristic_payload["reasons"]
            and not heuristic_payload["has_title_placeholder"]
            and not heuristic_payload["has_body_placeholder"]
        ):
            heuristic_payload = None

        placeholder_summary_payload = placeholder_summary or None
        layout_description: dict[str, Any] | None = None
        try:
            layout_description = generate_layout_description(
                layout_name or "",
                placeholder_records,
                (self._slide_width_emu or 0, self._slide_height_emu or 0),
            )
        except Exception:  # noqa: BLE001
            layout_description = None

        return LayoutInfo(
            name=layout_name,
            identifier=identifier,
            anchors=anchors,
            prototype_index=prototype_index,
            placeholder_summary=placeholder_summary_payload,
            heuristic=heuristic_payload,
            layout_description=layout_description,
        )

    @staticmethod
    def _matches_filter(value: str, keyword: str) -> bool:
        """フィルタ語との前方一致を確認する。"""
        if not value or not keyword:
            return True
        return value.casefold().startswith(keyword.casefold())

    def _determine_output_path(self, context: PipelineContext) -> Path:
        """出力パスを決定する。"""
        if self.options.output_path:
            return self.options.output_path

        context.workdir.mkdir(parents=True, exist_ok=True)
        if self.options.format == "yaml":
            return context.workdir / "template_spec.yaml"
        return context.workdir / "template_spec.json"

    @staticmethod
    def _determine_jobspec_path(spec_output_path: Path) -> Path:
        """jobspec.json の出力先パスを決定する。"""
        return spec_output_path.with_name("jobspec.json")

    def _save_template_spec(
        self, template_spec: TemplateSpec, output_path: Path
    ) -> None:
        """テンプレート仕様をファイルに保存する。"""
        if self.options.format == "yaml":
            import yaml

            data = template_spec.model_dump(mode="json", exclude_none=True)
            content = yaml.dump(
                data, allow_unicode=True, default_flow_style=False, indent=2
            )
        else:
            content = json.dumps(
                template_spec.model_dump(mode="json", exclude_none=True),
                indent=2,
                ensure_ascii=False,
            )

        output_path.write_text(content, encoding="utf-8")
        logger.info("テンプレート仕様を保存: %s", output_path)

    def _save_jobspec_scaffold(self, jobspec, output_path: Path) -> None:
        """ジョブスペック雛形をファイルに保存する。"""
        output_path.write_text(
            json.dumps(jobspec.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("ジョブスペック雛形を保存: %s", output_path)

    def _load_font_defaults(self) -> None:
        try:
            branding = extract_branding_config(self.options.template_path)
        except (BrandingExtractionError, BadZipFile, FileNotFoundError) as exc:
            logger.debug("branding 設定の抽出に失敗したため既定フォントを使用: %s", exc)
            return

        heading_payload = branding.fonts.get("heading") if branding.fonts else None
        body_payload = branding.fonts.get("body") if branding.fonts else None
        if heading_payload:
            self._heading_font_default = self._font_spec_from_payload(
                heading_payload, self._heading_font_default
            )
        if body_payload:
            self._body_font_default = self._font_spec_from_payload(
                body_payload, self._body_font_default
            )

    @staticmethod
    def _font_spec_from_payload(
        payload: dict[str, Any], fallback: FontSpec
    ) -> FontSpec:
        from .helpers import normalize_hex

        name = payload.get("name") or fallback.name
        size_pt = payload.get("size_pt") or fallback.size_pt
        color_hex = normalize_hex(payload.get("color_hex")) or fallback.color_hex
        bold = payload.get("bold")
        italic = payload.get("italic")
        return fallback.model_copy(
            update={
                "name": str(name),
                "size_pt": float(size_pt),
                "color_hex": color_hex,
                "bold": bool(bold) if bold is not None else fallback.bold,
                "italic": bool(italic) if italic is not None else fallback.italic,
            }
        )
