from __future__ import annotations

import logging

from ...models import Slide, SlideTextbox, TextboxParagraph
from .layout import LayoutBox

logger = logging.getLogger(__name__)


class TextboxMixin:
    def _apply_textboxes(self, slide, slide_spec: Slide) -> None:
        if not slide_spec.textboxes:
            return

        for textbox_spec in slide_spec.textboxes:
            fallback_box = self._resolve_textbox_fallback(textbox_spec)
            text_frame = self._obtain_text_frame(
                slide=slide,
                anchor_name=textbox_spec.anchor,
                fallback_box=fallback_box,
                strict_anchor=False,
            )
            if text_frame is None:
                msg = (
                    f"Shape with name '{textbox_spec.anchor}' not found in slide."
                    " テンプレートの図形名を確認してください。"
                )
                raise ValueError(msg)
            shape = getattr(text_frame, "_parent", None)
            if shape is not None:
                target_name = textbox_spec.anchor or textbox_spec.id
                if target_name:
                    try:
                        shape.name = target_name
                    except ValueError:
                        logger.debug(
                            "テキストボックス名 '%s' の設定に失敗",
                            target_name,
                            exc_info=True,
                        )
            self._write_textbox_content(textbox_spec, text_frame)

    def _write_textbox_content(
        self, textbox_spec: SlideTextbox, text_frame
    ) -> None:
        text_frame.clear()
        text_frame.word_wrap = True
        default_font = self._style.textbox.font or self._style.body_font
        default_paragraph = self._style.textbox.paragraph or TextboxParagraph()

        lines = textbox_spec.text.splitlines() or [""]
        for index, line in enumerate(lines):
            paragraph = (
                text_frame.paragraphs[0] if index == 0 else text_frame.add_paragraph()
            )
            paragraph.text = line
            self._apply_font(
                paragraph,
                textbox_spec.font,
                fallback=default_font,
            )
            self._apply_paragraph_style(
                paragraph,
                textbox_spec.paragraph,
                fallback=default_paragraph,
                preserve_level=False,
            )

    def _resolve_textbox_fallback(self, textbox_spec: SlideTextbox) -> LayoutBox:
        position = textbox_spec.position
        if position is not None:
            return LayoutBox(
                position.left_in,
                position.top_in,
                position.width_in,
                position.height_in,
            )
        fallback_box = self._style.textbox.fallback_box
        if fallback_box is not None:
            return LayoutBox(
                fallback_box.left_in,
                fallback_box.top_in,
                fallback_box.width_in,
                fallback_box.height_in,
            )
        return LayoutBox(1.0, 1.0, 8.0, 3.0)
