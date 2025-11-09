"""テンプレートファイルから図形・プレースホルダー情報を抽出する。"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from pptx import Presentation
from pptx.shapes.base import BaseShape
from pptx.shapes.placeholder import PlaceholderPicture, SlidePlaceholder

from ..models import (JobSpecScaffold, JobSpecScaffoldBounds,
                      JobSpecScaffoldMeta, JobSpecScaffoldPlaceholder,
                      JobSpecScaffoldSlide, LayoutInfo, ShapeInfo,
                      TemplateBlueprint, TemplateBlueprintSlide,
                      TemplateBlueprintSlot, TemplateSpec)
from .base import PipelineContext, PipelineStep

logger = logging.getLogger(__name__)

# SlideBullet拡張仕様で使用される可能性のあるアンカー名パターン
SLIDE_BULLET_ANCHORS = {"bullets", "bullet_list", "content", "body"}
JOBSPEC_SCHEMA_VERSION = "0.1"
MAX_SAMPLE_TEXT_LENGTH = 200


@dataclass
class TemplateExtractorOptions:
    """TemplateExtractor の設定オプション。"""

    template_path: Path
    output_path: Optional[Path] = None
    layout_filter: Optional[str] = None
    anchor_filter: Optional[str] = None
    format: str = "json"  # json または yaml
    layout_mode: str = "dynamic"


class TemplateExtractorStep:
    """テンプレートファイルから図形情報を抽出するステップ。"""
    
    name = "TemplateExtractor"
    
    def __init__(self, options: TemplateExtractorOptions) -> None:
        self.options = options
    
    def run(self, context: PipelineContext) -> None:
        """テンプレート抽出を実行する。"""
        logger.info("テンプレート抽出を開始: %s", self.options.template_path)
        
        try:
            template_spec = self.extract_template_spec()
            output_path = self._determine_output_path(context)
            self._save_template_spec(template_spec, output_path)
            jobspec_scaffold = self.build_jobspec_scaffold(template_spec)
            jobspec_path = self._determine_jobspec_path(output_path)
            self._save_jobspec_scaffold(jobspec_scaffold, jobspec_path)

            context.add_artifact("template_spec", template_spec)
            context.add_artifact("template_spec_path", output_path)
            context.add_artifact("jobspec_scaffold", jobspec_scaffold)
            context.add_artifact("jobspec_path", jobspec_path)

            logger.info("テンプレート抽出完了: %s (jobspec=%s)", output_path, jobspec_path)
            
        except Exception as exc:
            logger.error("テンプレート抽出に失敗: %s", exc)
            raise
    
    def extract_template_spec(self) -> TemplateSpec:
        """テンプレートファイルから仕様を抽出する。"""
        if not self.options.template_path.exists():
            raise FileNotFoundError(f"テンプレートファイルが見つかりません: {self.options.template_path}")

        try:
            presentation = Presentation(self.options.template_path)
        except Exception as exc:
            raise RuntimeError(f"テンプレートファイルの読み込みに失敗しました: {exc}") from exc

        layouts = []
        warnings = []
        errors = []
        
        for slide_layout in presentation.slide_layouts:
            try:
                layout_info = self._extract_layout_info(slide_layout)
                
                # レイアウトフィルタがある場合はチェック
                if self.options.layout_filter and not self._matches_filter(
                    layout_info.name, self.options.layout_filter
                ):
                    continue
                
                layouts.append(layout_info)
                
            except Exception as exc:
                error_msg = f"レイアウト '{slide_layout.name}' の抽出に失敗: {exc}"
                logger.warning(error_msg)
                errors.append(error_msg)
        
        blueprint = None
        layout_mode = (self.options.layout_mode or "dynamic").lower()
        if layout_mode not in {"dynamic", "static"}:
            layout_mode = "dynamic"
        if layout_mode == "static":
            blueprint = self._build_blueprint(layouts)

        return TemplateSpec(
            template_path=str(self.options.template_path),
            extracted_at=datetime.now(timezone.utc).isoformat(),
            layouts=layouts,
            warnings=warnings,
            errors=errors,
            layout_mode=layout_mode,  # type: ignore[arg-type]
            blueprint=blueprint,
        )
    
    def _extract_layout_info(self, slide_layout) -> LayoutInfo:
        """単一レイアウトから図形情報を抽出する。"""
        layout_name = slide_layout.name
        identifier = None
        try:
            layout_identifier = getattr(slide_layout, "slide_layout_id", None)
        except Exception:  # noqa: BLE001
            layout_identifier = None
        if layout_identifier is not None:
            identifier = str(layout_identifier)
        anchors = []

        for shape in slide_layout.shapes:
            try:
                shape_info = self._extract_shape_info(shape)
                
                # アンカーフィルタがある場合はチェック
                if self.options.anchor_filter and not self._matches_filter(
                    shape_info.name, self.options.anchor_filter
                ):
                    continue
                
                anchors.append(shape_info)
                
            except Exception as exc:
                error_msg = f"図形 '{shape.name}' の抽出エラー: {exc}"
                logger.warning(error_msg)
                
                # エラー付きの図形情報を作成
                error_shape = ShapeInfo(
                    name=getattr(shape, 'name', '不明な図形'),
                    shape_type="unknown",
                    left_in=0.0,
                    top_in=0.0,
                    width_in=0.0,
                    height_in=0.0,
                    error=error_msg,
                )
                anchors.append(error_shape)

        return LayoutInfo(name=layout_name, identifier=identifier, anchors=anchors)
    
    def _extract_shape_info(self, shape: BaseShape) -> ShapeInfo:
        """単一図形から情報を抽出する。"""
        # 基本属性の抽出
        name = getattr(shape, 'name', '')
        if not name:
            name = f"unnamed_shape_{id(shape)}"
        
        # 位置・サイズ情報（EMU単位からインチに変換）
        left_in = shape.left / 914400.0 if hasattr(shape, 'left') else 0.0
        top_in = shape.top / 914400.0 if hasattr(shape, 'top') else 0.0
        width_in = shape.width / 914400.0 if hasattr(shape, 'width') else 0.0
        height_in = shape.height / 914400.0 if hasattr(shape, 'height') else 0.0
        
        # 図形種別の判定
        shape_type = shape.__class__.__name__
        
        # テキスト内容の抽出
        text = None
        text_frame = getattr(shape, "text_frame", None)
        if text_frame is not None:
            frame_text = getattr(text_frame, "text", None)
            if isinstance(frame_text, str):
                text = frame_text
        if text is None:
            raw_text = getattr(shape, "text", None)
            if isinstance(raw_text, str):
                text = raw_text
        
        # プレースホルダー情報の抽出
        placeholder_format = None
        try:
            placeholder_format = shape.placeholder_format  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            # python-pptx は非プレースホルダー図形にアクセスすると ValueError を送出する
            placeholder_format = None
        is_placeholder = bool(
            isinstance(shape, (SlidePlaceholder, PlaceholderPicture))
            or getattr(shape, "is_placeholder", False)
            or placeholder_format is not None
        )
        placeholder_type = None
        if placeholder_format is not None:
            placeholder_kind = getattr(placeholder_format, "type", None)
            if hasattr(placeholder_kind, "name"):
                placeholder_type = str(getattr(placeholder_kind, "name"))
            elif placeholder_kind is not None:
                placeholder_type = str(placeholder_kind)
        
        # SlideBullet拡張仕様との競合チェック
        conflict = None
        if name.lower() in SLIDE_BULLET_ANCHORS:
            conflict = f"SlideBullet拡張仕様で使用される可能性のあるアンカー名: {name}"
        
        # 必須フィールドの欠落チェック
        missing_fields = []
        if not name or name.startswith("unnamed_"):
            missing_fields.append("name")
        if width_in <= 0:
            missing_fields.append("width")
        if height_in <= 0:
            missing_fields.append("height")
        
        return ShapeInfo(
            name=name,
            shape_type=shape_type,
            left_in=left_in,
            top_in=top_in,
            width_in=width_in,
            height_in=height_in,
            text=text,
            placeholder_type=placeholder_type,
            is_placeholder=is_placeholder,
            conflict=conflict,
            missing_fields=missing_fields,
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

    def _save_template_spec(self, template_spec: TemplateSpec, output_path: Path) -> None:
        """テンプレート仕様をファイルに保存する。"""
        if self.options.format == "yaml":
            import yaml
            data = template_spec.model_dump(mode="json", exclude_none=True)
            content = yaml.dump(data, allow_unicode=True, default_flow_style=False, indent=2)
        else:
            content = json.dumps(
                template_spec.model_dump(mode="json", exclude_none=True),
                indent=2,
                ensure_ascii=False,
            )

        output_path.write_text(content, encoding="utf-8")
        logger.info("テンプレート仕様を保存: %s", output_path)

    def build_jobspec_scaffold(self, template_spec: TemplateSpec) -> JobSpecScaffold:
        """テンプレート情報からジョブスペック雛形を生成する。"""
        template_path = self.options.template_path
        template_id = self._derive_template_id(template_path)
        meta = JobSpecScaffoldMeta(
            schema_version=JOBSPEC_SCHEMA_VERSION,
            template_path=str(template_path),
            template_id=template_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            layout_count=len(template_spec.layouts),
        )

        counters: defaultdict[str, int] = defaultdict(int)
        slides: list[JobSpecScaffoldSlide] = []

        for layout in template_spec.layouts:
            counters[layout.name] += 1
            sequence = counters[layout.name]
            slide_id = self._resolve_slide_id(layout, sequence)

            placeholders: list[JobSpecScaffoldPlaceholder] = []
            for index, anchor in enumerate(layout.anchors, start=1):
                anchor_name = anchor.name or f"shape_{index:02d}"
                bounds = JobSpecScaffoldBounds(
                    left_in=anchor.left_in,
                    top_in=anchor.top_in,
                    width_in=anchor.width_in,
                    height_in=anchor.height_in,
                )
                placeholder = JobSpecScaffoldPlaceholder(
                    anchor=anchor_name,
                    kind=self._infer_placeholder_kind(anchor),
                    placeholder_type=anchor.placeholder_type,
                    shape_type=anchor.shape_type,
                    is_placeholder=anchor.is_placeholder,
                    bounds=bounds,
                    sample_text=self._sanitize_sample_text(anchor.text),
                    notes=self._collect_placeholder_notes(anchor),
                )
                placeholders.append(placeholder)

            slides.append(
                JobSpecScaffoldSlide(
                    id=slide_id,
                    layout=layout.name,
                    sequence=sequence,
                    placeholders=placeholders,
                )
            )

        return JobSpecScaffold(meta=meta, slides=slides)

    def _build_blueprint(self, layouts: list[LayoutInfo]) -> TemplateBlueprint:
        slides: list[TemplateBlueprintSlide] = []

        for index, layout in enumerate(layouts, start=1):
            slide_id = self._resolve_slide_id(layout, index)
            slot_sequence = 1
            slots: list[TemplateBlueprintSlot] = []
            for anchor in layout.anchors:
                content_type = self._infer_placeholder_kind(anchor)
                slot_id = f"{slide_id}.slot{slot_sequence:02d}"
                slot_sequence += 1
                required = self._is_required_slot(anchor)
                slots.append(
                    TemplateBlueprintSlot(
                        slot_id=slot_id,
                        anchor=anchor.name,
                        content_type=content_type,
                        required=required,
                        intent_tags=self._derive_slot_intent_tags(anchor, layout.name),
                    )
                )

            slides.append(
                TemplateBlueprintSlide(
                    slide_id=slide_id,
                    layout=layout.name,
                    required=True,
                    intent_tags=self._derive_layout_intent_tags(layout.name),
                    slots=slots,
                )
            )

        return TemplateBlueprint(slides=slides)

    def _save_jobspec_scaffold(self, jobspec: JobSpecScaffold, output_path: Path) -> None:
        """ジョブスペック雛形をファイルに保存する。"""
        output_path.write_text(
            json.dumps(jobspec.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("ジョブスペック雛形を保存: %s", output_path)

    def _resolve_slide_id(self, layout: LayoutInfo, sequence: int) -> str:
        base = None
        if layout.identifier:
            base = f"id_{layout.identifier}"
        if not base:
            base = self._slugify_layout_name(layout.name)
        if not base:
            base = "slide"
        suffix = f"{sequence:02d}"
        return f"{base}-{suffix}"

    def _infer_placeholder_kind(
        self, shape: ShapeInfo
    ) -> Literal["text", "image", "table", "chart", "shape", "other"]:
        placeholder_type = (shape.placeholder_type or "").upper()
        if placeholder_type in {"TITLE", "CENTER_TITLE", "SUBTITLE", "BODY", "CONTENT", "TEXT"}:
            return "text"
        if placeholder_type in {"PICTURE", "CLIP_ART", "BITMAP", "OBJECT"}:
            return "image"
        if placeholder_type in {"TABLE"}:
            return "table"
        if placeholder_type in {"CHART"}:
            return "chart"

        shape_type = (shape.shape_type or "").lower()
        if "chart" in shape_type or "graph" in shape_type:
            return "chart"
        if "table" in shape_type:
            return "table"
        if "picture" in shape_type or "image" in shape_type or "bitmap" in shape_type:
            return "image"
        if shape.text:
            return "text"
        return "other"

    def _is_required_slot(self, shape: ShapeInfo) -> bool:
        placeholder_type = (shape.placeholder_type or "").upper()
        if placeholder_type in {"TITLE", "CENTER_TITLE", "BODY"}:
            return True
        if placeholder_type in {"SUBTITLE", "CONTENT"}:
            return False
        shape_type = (shape.shape_type or "").lower()
        if "picture" in shape_type or "image" in shape_type:
            return False
        if "chart" in shape_type or "table" in shape_type:
            return False
        return True

    @staticmethod
    def _derive_slot_intent_tags(shape: ShapeInfo, layout_name: str | None) -> list[str]:
        del layout_name  # 現状は形状からの推測に限定
        placeholder_type = (shape.placeholder_type or "").upper()
        if placeholder_type in {"TITLE", "CENTER_TITLE"}:
            return ["headline"]
        if placeholder_type in {"SUBTITLE"}:
            return ["subheadline"]
        if placeholder_type in {"BODY", "CONTENT", "TEXT"}:
            return ["body"]
        return []

    @staticmethod
    def _derive_layout_intent_tags(layout_name: str | None) -> list[str]:
        name = (layout_name or "").lower()
        if "title" in name or "cover" in name:
            return ["opening"]
        if "closing" in name:
            return ["closing"]
        if "agenda" in name:
            return ["agenda"]
        if "summary" in name:
            return ["summary"]
        return []

    def _sanitize_sample_text(self, text: str | None) -> str | None:
        if text is None:
            return None
        cleaned_lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not cleaned_lines:
            cleaned = text.strip()
            if not cleaned:
                return None
        else:
            cleaned = "\n".join(cleaned_lines)
        if len(cleaned) > MAX_SAMPLE_TEXT_LENGTH:
            return cleaned[:MAX_SAMPLE_TEXT_LENGTH].rstrip() + "..."
        return cleaned

    def _collect_placeholder_notes(self, shape: ShapeInfo) -> list[str]:
        notes: list[str] = []
        if shape.conflict:
            notes.append(shape.conflict)
        if shape.missing_fields:
            notes.append("missing_fields: " + ", ".join(shape.missing_fields))
        if shape.error:
            notes.append(shape.error)
        if shape.width_in <= 0 or shape.height_in <= 0:
            notes.append("size_not_positive")
        return notes

    @staticmethod
    def _slugify_layout_name(name: str | None) -> str:
        normalized = unicodedata.normalize("NFKC", (name or "").strip())
        normalized = normalized.replace(" ", "_")
        normalized = re.sub(r"[\s/\\]+", "_", normalized)
        normalized = re.sub(r"[^0-9A-Za-z_\-一-龯ぁ-んァ-ンー]+", "", normalized)
        return normalized.lower()

    @staticmethod
    def _derive_template_id(path: Path) -> str:
        stem = unicodedata.normalize("NFKC", path.stem)
        stem = re.sub(r"[^0-9A-Za-z_\-一-龯ぁ-んァ-ンー]+", "", stem)
        return stem or "template"


class TemplateExtractor:
    """スタンドアロンでテンプレート抽出を行うクラス。"""
    
    def __init__(self, options: TemplateExtractorOptions) -> None:
        self.options = options
        self.step = TemplateExtractorStep(options)
    
    def extract(self) -> TemplateSpec:
        """テンプレート抽出を実行してTemplateSpecを返す。"""
        return self.step.extract_template_spec()

    def build_jobspec_scaffold(self, template_spec: TemplateSpec) -> JobSpecScaffold:
        """テンプレート仕様からジョブスペック雛形を構築する。"""
        return self.step.build_jobspec_scaffold(template_spec)

    def save_jobspec_scaffold(self, jobspec: JobSpecScaffold, output_path: Path) -> None:
        """ジョブスペック雛形を保存する。"""
        self.step._save_jobspec_scaffold(jobspec, output_path)

    def extract_and_save(self, output_path: Optional[Path] = None) -> Path:
        """テンプレート抽出を実行してファイルに保存する。"""
        template_spec = self.extract()
        jobspec_scaffold = self.build_jobspec_scaffold(template_spec)
        
        if output_path is None:
            if self.options.format == "yaml":
                output_path = Path("template_spec.yaml")
            else:
                output_path = Path("template_spec.json")

        self.step._save_template_spec(template_spec, output_path)
        jobspec_path = self.step._determine_jobspec_path(output_path)
        self.step._save_jobspec_scaffold(jobspec_scaffold, jobspec_path)
        return output_path
