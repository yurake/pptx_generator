"""PPTX 生成を担うステップ。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.util import Inches, Pt

from ..models import FontSpec, JobSpec, Slide
from .base import PipelineContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RenderingOptions:
    template_path: Path | None = None
    output_filename: str = "proposal.pptx"
    default_font_name: str = "Yu Gothic"
    default_font_size: float = 18.0
    default_font_color: str = "#333333"


class SimpleRendererStep:
    """最小機能の PPTX レンダラー。"""

    name = "renderer"

    def __init__(self, options: RenderingOptions | None = None) -> None:
        self.options = options or RenderingOptions()

    def run(self, context: PipelineContext) -> None:
        presentation = self._load_template()
        self._render_slides(presentation, context.spec)
        output_path = self._save(presentation, context.workdir)
        context.add_artifact("pptx_path", output_path)
        logger.info("PPTX を出力しました: %s", output_path)

    def _load_template(self) -> Presentation:
        if self.options.template_path and self.options.template_path.exists():
            logger.debug("テンプレートを使用: %s", self.options.template_path)
            return Presentation(self.options.template_path)
        logger.debug("既定テンプレートを利用")
        return Presentation()

    def _render_slides(self, presentation: Presentation, spec: JobSpec) -> None:
        for slide_spec in spec.slides:
            layout = self._resolve_layout(presentation, slide_spec)
            slide = presentation.slides.add_slide(layout)
            self._apply_title(slide, slide_spec)
            self._apply_bullets(slide, slide_spec)

    def _resolve_layout(self, presentation: Presentation, slide_spec: Slide):
        for layout in presentation.slide_layouts:
            if layout.name == slide_spec.layout:
                return layout
        logger.debug("レイアウト '%s' が見つからないため既定を使用", slide_spec.layout)
        return presentation.slide_layouts[1]

    def _apply_title(self, slide, slide_spec: Slide) -> None:
        if slide_spec.title is None:
            return
        title_shape = slide.shapes.title
        if title_shape is not None:
            title_shape.text = slide_spec.title
            return
        textbox = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(8.0), Inches(1.0))
        textbox.text = slide_spec.title

    def _apply_bullets(self, slide, slide_spec: Slide) -> None:
        if not slide_spec.bullets:
            return
        body_shape = self._find_body_placeholder(slide)
        text_frame = body_shape.text_frame
        text_frame.clear()
        for index, bullet in enumerate(slide_spec.bullets):
            paragraph = text_frame.paragraphs[0] if index == 0 else text_frame.add_paragraph()
            paragraph.text = bullet.text
            paragraph.level = bullet.level
            self._apply_font(paragraph, bullet.font)

    def _find_body_placeholder(self, slide):
        for shape in slide.placeholders:
            if shape.placeholder_format.type == PP_PLACEHOLDER.BODY:
                return shape
        logger.debug("本文用プレースホルダがないためテキストボックスを追加")
        return slide.shapes.add_textbox(Inches(1.0), Inches(1.5), Inches(8.0), Inches(4.5))

    def _apply_font(self, paragraph, font_spec: FontSpec | None) -> None:
        font = paragraph.font
        if font_spec is None:
            font.name = self.options.default_font_name
            font.size = Pt(self.options.default_font_size)
            font.color.rgb = RGBColor.from_string(self.options.default_font_color.lstrip("#"))
            return
        font.name = font_spec.name
        font.size = Pt(font_spec.size_pt)
        font.bold = font_spec.bold
        font.italic = font_spec.italic
        font.color.rgb = RGBColor.from_string(font_spec.color_hex.lstrip("#"))

    def _save(self, presentation: Presentation, workdir: Path) -> Path:
        output_dir = workdir / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / self.options.output_filename
        presentation.save(output_path)
        return output_path
