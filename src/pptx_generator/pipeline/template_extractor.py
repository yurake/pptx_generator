"""テンプレートファイルから図形・プレースホルダー情報を抽出する。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pptx import Presentation
from pptx.shapes.base import BaseShape
from pptx.shapes.placeholder import PlaceholderPicture, SlidePlaceholder

from ..models import LayoutInfo, ShapeInfo, TemplateSpec
from .base import PipelineContext, PipelineStep

logger = logging.getLogger(__name__)

# SlideBullet拡張仕様で使用される可能性のあるアンカー名パターン
SLIDE_BULLET_ANCHORS = {"bullets", "bullet_list", "content", "body"}


@dataclass
class TemplateExtractorOptions:
    """TemplateExtractor の設定オプション。"""
    
    template_path: Path
    output_path: Optional[Path] = None
    layout_filter: Optional[str] = None
    anchor_filter: Optional[str] = None
    format: str = "json"  # json または yaml


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
            
            context.add_artifact("template_spec", template_spec)
            context.add_artifact("template_spec_path", output_path)
            
            logger.info("テンプレート抽出完了: %s", output_path)
            
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
        
        return TemplateSpec(
            template_path=str(self.options.template_path),
            extracted_at=datetime.now(timezone.utc).isoformat(),
            layouts=layouts,
            warnings=warnings,
            errors=errors,
        )
    
    def _extract_layout_info(self, slide_layout) -> LayoutInfo:
        """単一レイアウトから図形情報を抽出する。"""
        layout_name = slide_layout.name
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
        
        return LayoutInfo(name=layout_name, anchors=anchors)
    
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
        placeholder_format = getattr(shape, "placeholder_format", None)
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
        
        # デフォルトは outputs ディレクトリ
        outputs_dir = context.workdir / "outputs"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        
        if self.options.format == "yaml":
            return outputs_dir / "template_spec.yaml"
        return outputs_dir / "template_spec.json"
    
    def _save_template_spec(self, template_spec: TemplateSpec, output_path: Path) -> None:
        """テンプレート仕様をファイルに保存する。"""
        if self.options.format == "yaml":
            import yaml
            data = template_spec.model_dump()
            content = yaml.dump(data, allow_unicode=True, default_flow_style=False, indent=2)
        else:
            import json
            content = json.dumps(template_spec.model_dump(), indent=2, ensure_ascii=False)
        
        output_path.write_text(content, encoding="utf-8")
        logger.info("テンプレート仕様を保存: %s", output_path)


class TemplateExtractor:
    """スタンドアロンでテンプレート抽出を行うクラス。"""
    
    def __init__(self, options: TemplateExtractorOptions) -> None:
        self.options = options
        self.step = TemplateExtractorStep(options)
    
    def extract(self) -> TemplateSpec:
        """テンプレート抽出を実行してTemplateSpecを返す。"""
        return self.step.extract_template_spec()
    
    def extract_and_save(self, output_path: Optional[Path] = None) -> Path:
        """テンプレート抽出を実行してファイルに保存する。"""
        template_spec = self.extract()
        
        if output_path is None:
            if self.options.format == "yaml":
                output_path = Path("template_spec.yaml")
            else:
                output_path = Path("template_spec.json")
        
        self.step._save_template_spec(template_spec, output_path)
        return output_path
