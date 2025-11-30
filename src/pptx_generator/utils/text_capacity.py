"""Utility helpers to estimate text capacity for a textbox."""

from __future__ import annotations

from typing import Final

from ..models import (FontSpec, TextCapacity, TextFramePadding,
                      TextboxParagraph)

# Baseline heuristics derived from historical layout_validation implementation.
_DEFAULT_FONT_SIZE_PT: Final[float] = 18.0
_DEFAULT_LINE_SPACING_RATIO: Final[float] = 1.2
_MIN_LINE_HEIGHT_IN: Final[float] = 0.1
_CHARS_PER_INCH_BASELINE: Final[float] = 20.0
_BULLET_INDENT_IN: Final[float] = 0.25


def estimate_text_capacity(
    *,
    width_in: float | int | None,
    height_in: float | int | None,
    font: FontSpec | None = None,
    paragraph: TextboxParagraph | None = None,
    padding: TextFramePadding | None = None,
) -> TextCapacity:
    """Estimate text capacity metrics for a textbox.

    Parameters
    ----------
    width_in, height_in
        Dimensions of the textbox in inches.
    font
        Font specification extracted from the template (name/size/color/bold/italic).
    paragraph
        Paragraph settings such as line spacing, level, and indents.
    padding
        Text frame padding (margins) applied to the textbox.
    """

    width = float(width_in or 0.0)
    height = float(height_in or 0.0)
    if width <= 0 or height <= 0:
        return TextCapacity(total_chars=0, chars_per_line=0, max_lines=0)

    font_size = _resolve_font_size(font)
    line_spacing_pt = _resolve_line_spacing(paragraph, font_size)
    line_height_in = max(line_spacing_pt / 72.0, _MIN_LINE_HEIGHT_IN)

    padding_left, padding_right, padding_top, padding_bottom = _resolve_padding(padding)
    inner_width = max(width - padding_left - padding_right, 0.0)
    inner_height = max(height - padding_top - padding_bottom, 0.0)

    indent_left, indent_right = _resolve_indents(paragraph)
    indent_left += _indent_from_level(paragraph.level if paragraph else 0)

    usable_width = max(inner_width - indent_left - indent_right, 0.0)
    max_lines = int(inner_height / line_height_in) if inner_height > 0 else 0

    char_density = _resolve_char_density(font_size)
    chars_per_line = int(usable_width * char_density) if usable_width > 0 else 0
    total_chars = max_lines * chars_per_line

    return TextCapacity(
        total_chars=max(total_chars, 0),
        chars_per_line=max(chars_per_line, 0),
        max_lines=max(max_lines, 0),
    )


def _resolve_font_size(font: FontSpec | None) -> float:
    if font and font.size_pt and font.size_pt > 0:
        return float(font.size_pt)
    return _DEFAULT_FONT_SIZE_PT


def _resolve_line_spacing(paragraph: TextboxParagraph | None, font_size: float) -> float:
    if paragraph and paragraph.line_spacing_pt and paragraph.line_spacing_pt > 0:
        return float(paragraph.line_spacing_pt)
    return font_size * _DEFAULT_LINE_SPACING_RATIO


def _resolve_padding(padding: TextFramePadding | None) -> tuple[float, float, float, float]:
    if padding is None:
        return (0.0, 0.0, 0.0, 0.0)
    return (
        max(float(padding.left_in or 0.0), 0.0),
        max(float(padding.right_in or 0.0), 0.0),
        max(float(padding.top_in or 0.0), 0.0),
        max(float(padding.bottom_in or 0.0), 0.0),
    )


def _resolve_indents(paragraph: TextboxParagraph | None) -> tuple[float, float]:
    if paragraph is None:
        return (0.0, 0.0)
    left = max(float(paragraph.left_indent_in or 0.0), 0.0)
    right = max(float(paragraph.right_indent_in or 0.0), 0.0)
    return (left, right)


def _indent_from_level(level: int | None) -> float:
    if level is None or level <= 0:
        return 0.0
    return max(level, 0) * _BULLET_INDENT_IN


def _resolve_char_density(font_size: float) -> float:
    if font_size <= 0:
        font_size = _DEFAULT_FONT_SIZE_PT
    ratio = _DEFAULT_FONT_SIZE_PT / font_size
    ratio = min(max(ratio, 0.2), 4.0)
    density = _CHARS_PER_INCH_BASELINE * ratio
    return max(density, 1.0)


__all__ = ["estimate_text_capacity"]
