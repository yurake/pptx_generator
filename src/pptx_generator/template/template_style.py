"""Utilities for working with template style defaults."""

from __future__ import annotations

import logging
from pathlib import Path

from .branding_extractor import BrandingExtractionError, extract_branding_config
from ..models import (
    FontSpec,
    TemplateChartDefaults,
    TemplateColorPalette,
    TemplateImageDefaults,
    TemplateStyle,
    TemplateTableDefaults,
    TemplateTextboxDefaults,
    TextboxParagraph,
    TextboxPosition,
)
from ..settings import BrandingConfig, BrandingFont, BoxSpec, ParagraphStyle

logger = logging.getLogger(__name__)


def _font_from_branding(font: BrandingFont) -> FontSpec:
    return FontSpec(
        name=font.name,
        size_pt=float(font.size_pt),
        color_hex=font.color_hex,
        bold=bool(font.bold),
        italic=bool(font.italic),
    )


def _paragraph_from_branding(style: ParagraphStyle) -> TextboxParagraph:
    return TextboxParagraph(
        align=style.align,
        line_spacing_pt=style.line_spacing_pt,
        space_before_pt=style.space_before_pt,
        space_after_pt=style.space_after_pt,
        level=style.level if style.level is not None else 0,
        left_indent_in=style.left_indent_in,
        right_indent_in=style.right_indent_in,
        first_line_indent_in=style.first_line_indent_in,
    )


def _position_from_box(box: BoxSpec) -> TextboxPosition:
    return TextboxPosition(
        left_in=box.left_in,
        top_in=box.top_in,
        width_in=box.width_in,
        height_in=box.height_in,
    )


def template_style_from_branding(config: BrandingConfig) -> TemplateStyle:
    heading_font = _font_from_branding(config.heading_font)
    body_font = _font_from_branding(config.body_font)
    colors = TemplateColorPalette(
        primary=config.primary_color,
        secondary=config.secondary_color,
        accent=config.accent_color,
        background=config.background_color,
    )

    textbox_defaults = TemplateTextboxDefaults(
        fallback_box=_position_from_box(config.components.textbox.fallback_box),
        font=_font_from_branding(config.components.textbox.font),
        paragraph=_paragraph_from_branding(config.components.textbox.paragraph),
    )

    table_defaults = TemplateTableDefaults(
        fallback_box=_position_from_box(config.components.table.fallback_box),
        header_font=_font_from_branding(config.components.table.header.font),
        header_fill_color=config.components.table.header.fill_color,
        body_font=_font_from_branding(config.components.table.body.font),
        body_fill_color=config.components.table.body.fill_color,
        zebra_fill_color=config.components.table.body.zebra_fill_color,
    )

    chart_defaults = TemplateChartDefaults(
        fallback_box=_position_from_box(config.components.chart.fallback_box),
        palette=list(config.components.chart.palette),
        axis_font=_font_from_branding(config.components.chart.axis.font),
        data_labels_enabled=config.components.chart.data_labels.enabled,
        data_labels_format=config.components.chart.data_labels.format,
    )

    image_defaults = TemplateImageDefaults(
        fallback_box=_position_from_box(config.components.image.fallback_box),
        sizing=config.components.image.sizing,
    )

    return TemplateStyle(
        heading_font=heading_font,
        body_font=body_font,
        colors=colors,
        textbox=textbox_defaults,
        table=table_defaults,
        chart=chart_defaults,
        image=image_defaults,
    )


def extract_template_style(template: Path) -> tuple[TemplateStyle, dict[str, object]]:
    try:
        extraction = extract_branding_config(template)
    except BrandingExtractionError as exc:
        logger.warning("テンプレートスタイルの抽出に失敗したため既定値を使用: %s", exc)
        style = TemplateStyle.default()
        artifact = {
            "source": {
                "type": "default",
                "error": str(exc),
            }
        }
        return style, artifact

    branding_config = extraction.to_branding_config(fallback=BrandingConfig.default())
    style = template_style_from_branding(branding_config)
    artifact = {
        "source": {"type": "template", "template": str(template)},
        "config": extraction.to_branding_payload(),
    }
    return style, artifact
