from __future__ import annotations

from ...models import Slide


class NotesMixin:
    def _apply_notes(self, slide, slide_spec: Slide) -> None:
        if not slide_spec.notes:
            return
        notes_slide = slide.notes_slide
        text_frame = notes_slide.notes_text_frame

        text_frame.clear()
        lines = slide_spec.notes.splitlines() or [slide_spec.notes]
        for index, line in enumerate(lines):
            paragraph = (
                text_frame.paragraphs[0] if index == 0 else text_frame.add_paragraph()
            )
            paragraph.text = line
            self._set_font(paragraph, self._style.body_font)
            paragraph.level = 0
