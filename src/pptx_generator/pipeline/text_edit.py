from __future__ import annotations

from pptx.dml.color import RGBColor


def overwrite_text_frame_preserving_style(text_frame, new_text: str) -> None:
    """
    text_frame のテキストを差し替える。既存のラン／段落の書式をベースに再適用する。
    """
    if text_frame is None:
        return

    paragraphs = list(getattr(text_frame, "paragraphs", []))
    if paragraphs:
        base_paragraph = paragraphs[0]
    else:
        base_paragraph = text_frame.add_paragraph()
    base_run = base_paragraph.runs[0] if base_paragraph.runs else base_paragraph.add_run()

    run_style = _snapshot_run_style(base_run.font)
    paragraph_style = _snapshot_paragraph_style(base_paragraph)
    frame_style = _snapshot_text_frame_style(text_frame)

    lines = new_text.splitlines() or [""]

    text_frame.clear()
    _apply_text_frame_style(text_frame, frame_style)

    for index, line in enumerate(lines):
        paragraph = text_frame.paragraphs[0] if index == 0 else text_frame.add_paragraph()
        paragraph.text = line
        _apply_paragraph_style(paragraph, paragraph_style)
        if not paragraph.runs:
            paragraph.add_run()
        run = paragraph.runs[0]
        _apply_run_style(run.font, run_style)


def _snapshot_run_style(font) -> dict[str, object | None]:
    color = getattr(getattr(font, "color", None), "rgb", None)
    return {
        "name": getattr(font, "name", None),
        "size": getattr(font, "size", None),
        "bold": getattr(font, "bold", None),
        "italic": getattr(font, "italic", None),
        "underline": getattr(font, "underline", None),
        "color_rgb": color if isinstance(color, RGBColor) else None,
    }


def _apply_run_style(font, style: dict[str, object | None]) -> None:
    if style.get("name") is not None:
        font.name = style["name"]
    if style.get("size") is not None:
        font.size = style["size"]
    if style.get("bold") is not None:
        font.bold = style["bold"]
    if style.get("italic") is not None:
        font.italic = style["italic"]
    if style.get("underline") is not None:
        font.underline = style["underline"]
    if style.get("color_rgb") is not None:
        font.color.rgb = style["color_rgb"]


def _snapshot_paragraph_style(paragraph) -> dict[str, object | None]:
    return {
        "alignment": getattr(paragraph, "alignment", None),
        "level": getattr(paragraph, "level", None),
        "line_spacing": getattr(paragraph, "line_spacing", None),
        "space_before": getattr(paragraph, "space_before", None),
        "space_after": getattr(paragraph, "space_after", None),
        "left_indent": getattr(paragraph, "left_indent", None),
        "right_indent": getattr(paragraph, "right_indent", None),
        "first_line_indent": getattr(paragraph, "first_line_indent", None),
    }


def _apply_paragraph_style(paragraph, style: dict[str, object | None]) -> None:
    if style.get("alignment") is not None:
        paragraph.alignment = style["alignment"]
    if style.get("level") is not None:
        paragraph.level = style["level"]
    if style.get("line_spacing") is not None and hasattr(paragraph, "line_spacing"):
        paragraph.line_spacing = style["line_spacing"]
    if style.get("space_before") is not None and hasattr(paragraph, "space_before"):
        paragraph.space_before = style["space_before"]
    if style.get("space_after") is not None and hasattr(paragraph, "space_after"):
        paragraph.space_after = style["space_after"]
    if style.get("left_indent") is not None and hasattr(paragraph, "left_indent"):
        paragraph.left_indent = style["left_indent"]
    if style.get("right_indent") is not None and hasattr(paragraph, "right_indent"):
        paragraph.right_indent = style["right_indent"]
    if style.get("first_line_indent") is not None and hasattr(paragraph, "first_line_indent"):
        paragraph.first_line_indent = style["first_line_indent"]


def _snapshot_text_frame_style(text_frame) -> dict[str, object | None]:
    return {
        "word_wrap": getattr(text_frame, "word_wrap", None),
        "vertical_anchor": getattr(text_frame, "vertical_anchor", None),
        "auto_size": getattr(text_frame, "auto_size", None),
        "margin_left": getattr(text_frame, "margin_left", None),
        "margin_right": getattr(text_frame, "margin_right", None),
        "margin_top": getattr(text_frame, "margin_top", None),
        "margin_bottom": getattr(text_frame, "margin_bottom", None),
    }


def _apply_text_frame_style(text_frame, style: dict[str, object | None]) -> None:
    if style.get("word_wrap") is not None:
        text_frame.word_wrap = style["word_wrap"]
    if style.get("vertical_anchor") is not None:
        text_frame.vertical_anchor = style["vertical_anchor"]
    if style.get("auto_size") is not None:
        text_frame.auto_size = style["auto_size"]
    if style.get("margin_left") is not None:
        text_frame.margin_left = style["margin_left"]
    if style.get("margin_right") is not None:
        text_frame.margin_right = style["margin_right"]
    if style.get("margin_top") is not None:
        text_frame.margin_top = style["margin_top"]
    if style.get("margin_bottom") is not None:
        text_frame.margin_bottom = style["margin_bottom"]


__all__ = ["overwrite_text_frame_preserving_style"]
