from __future__ import annotations

from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from ...models import FontSpec, TemplateStyle, TextboxParagraph


class StylingMixin:
    _style: TemplateStyle

    def _set_font(self, paragraph, font_spec: FontSpec) -> None:
        font = paragraph.font
        font.name = font_spec.name
        font.size = Pt(font_spec.size_pt)
        font.bold = font_spec.bold
        font.italic = font_spec.italic
        font.color.rgb = RGBColor.from_string(font_spec.color_hex.lstrip("#"))

    def _apply_font(
        self,
        paragraph,
        font_spec: FontSpec | None,
        *,
        fallback: FontSpec,
    ) -> None:
        target = font_spec or fallback
        self._set_font(paragraph, target)

    def _apply_paragraph_style(
        self,
        paragraph,
        paragraph_spec: TextboxParagraph | None,
        *,
        fallback: TextboxParagraph | None,
        preserve_level: bool,
    ) -> None:
        base = fallback or TextboxParagraph()
        level = (
            paragraph_spec.level
            if paragraph_spec and paragraph_spec.level is not None
            else base.level
        )
        if not preserve_level or paragraph.level is None:
            paragraph.level = level if level is not None else (paragraph.level or 0)

        align = (
            paragraph_spec.align
            if paragraph_spec and paragraph_spec.align
            else base.align
        )
        if align:
            paragraph.alignment = self._resolve_alignment(align)

        line_spacing = (
            paragraph_spec.line_spacing_pt
            if paragraph_spec and paragraph_spec.line_spacing_pt is not None
            else base.line_spacing_pt
        )
        if line_spacing is not None:
            paragraph.line_spacing = Pt(line_spacing)

        space_before = (
            paragraph_spec.space_before_pt
            if paragraph_spec and paragraph_spec.space_before_pt is not None
            else base.space_before_pt
        )
        if space_before is not None:
            paragraph.space_before = Pt(space_before)

        space_after = (
            paragraph_spec.space_after_pt
            if paragraph_spec and paragraph_spec.space_after_pt is not None
            else base.space_after_pt
        )
        if space_after is not None:
            paragraph.space_after = Pt(space_after)

        paragraph_properties = paragraph._p.get_or_add_pPr()
        left_indent = (
            paragraph_spec.left_indent_in
            if paragraph_spec and paragraph_spec.left_indent_in is not None
            else base.left_indent_in
        )
        if left_indent is not None:
            paragraph_properties.set("marL", str(int(Inches(left_indent))))

        right_indent = (
            paragraph_spec.right_indent_in
            if paragraph_spec and paragraph_spec.right_indent_in is not None
            else base.right_indent_in
        )
        if right_indent is not None:
            paragraph_properties.set("marR", str(int(Inches(right_indent))))

        first_line_indent = (
            paragraph_spec.first_line_indent_in
            if paragraph_spec and paragraph_spec.first_line_indent_in is not None
            else base.first_line_indent_in
        )
        if first_line_indent is not None:
            paragraph_properties.set("indent", str(int(Inches(first_line_indent))))

    @staticmethod
    def _resolve_alignment(align: str) -> PP_ALIGN:
        mapping = {
            "left": PP_ALIGN.LEFT,
            "center": PP_ALIGN.CENTER,
            "right": PP_ALIGN.RIGHT,
            "justify": PP_ALIGN.JUSTIFY,
            "distributed": PP_ALIGN.DISTRIBUTE,
        }
        return mapping.get(align.lower(), PP_ALIGN.LEFT)

    @staticmethod
    def _apply_chart_axis_number_format(chart, labels_format: str | None) -> None:
        if not labels_format:
            return
        if hasattr(chart, "value_axis"):
            chart.value_axis.tick_labels.number_format = labels_format

    @staticmethod
    def _apply_single_axis_font(target_font, source: FontSpec) -> None:
        target_font.name = source.name
        target_font.size = Pt(source.size_pt)
        target_font.color.rgb = RGBColor.from_string(source.color_hex.lstrip("#"))
        target_font.bold = source.bold
        target_font.italic = source.italic

    @classmethod
    def _apply_chart_axes_font(cls, chart, axis_font: FontSpec) -> None:
        if hasattr(chart, "category_axis"):
            cls._apply_single_axis_font(
                chart.category_axis.tick_labels.font,
                axis_font,
            )
        if hasattr(chart, "value_axis"):
            cls._apply_single_axis_font(
                chart.value_axis.tick_labels.font,
                axis_font,
            )

    @staticmethod
    def _configure_chart_legend(chart) -> None:
        if getattr(chart, "has_legend", False) and chart.has_legend:
            chart.legend.include_in_layout = False
