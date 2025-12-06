from __future__ import annotations

from ...models import Slide, SlideBullet, TextboxParagraph
from .layout import LayoutBox


class BulletMixin:
    def _apply_bullets(self, slide, slide_spec: Slide) -> None:
        groups = slide_spec.bullets
        if not groups:
            return

        fallback_items: list[SlideBullet] = []
        used_anchors: set[str] = set()
        default_paragraph_style = self._style.textbox.paragraph or TextboxParagraph()
        default_font = self._style.textbox.font or self._style.body_font

        for group in groups:
            anchor_name = group.anchor
            if anchor_name:
                if anchor_name in used_anchors:
                    raise ValueError(
                        f"箇条書きのアンカー '{anchor_name}' が複数のグループで指定されています。"
                        "図形名はグループごとに一意にしてください。"
                    )
                used_anchors.add(anchor_name)
                self._render_bullet_group_to_anchor(
                    slide,
                    anchor_name,
                    group.items,
                    paragraph_style=default_paragraph_style,
                )
            else:
                fallback_items.extend(group.items)

        if fallback_items:
            target_shape = self._find_body_placeholder(slide)
            self._write_bullets_to_text_frame(
                target_shape.text_frame,
                fallback_items,
                paragraph_style=default_paragraph_style,
                default_font=default_font,
            )

    def _render_bullet_group_to_anchor(
        self,
        slide,
        anchor_name: str,
        bullets: list[SlideBullet],
        *,
        paragraph_style: TextboxParagraph,
    ) -> None:
        fallback_box = self._style.textbox.fallback_box
        if fallback_box is not None:
            box = LayoutBox(
                fallback_box.left_in,
                fallback_box.top_in,
                fallback_box.width_in,
                fallback_box.height_in,
            )
        else:
            box = LayoutBox(1.0, 1.0, 8.0, 3.0)
        text_frame = self._obtain_text_frame(
            slide=slide,
            anchor_name=anchor_name,
            fallback_box=box,
            strict_anchor=True,
        )

        if text_frame is None:
            raise ValueError(
                f"Shape with name '{anchor_name}' not found in slide. "
                "テンプレートの図形名を確認してください。"
            )
        self._write_bullets_to_text_frame(
            text_frame,
            bullets,
            paragraph_style=paragraph_style,
            default_font=self._style.textbox.font or self._style.body_font,
        )

    def _write_bullets_to_text_frame(
        self,
        text_frame,
        bullets: list[SlideBullet],
        *,
        paragraph_style: TextboxParagraph,
        default_font,
    ) -> None:
        text_frame.clear()
        text_frame.word_wrap = True
        for index, bullet in enumerate(bullets):
            paragraph = (
                text_frame.paragraphs[0] if index == 0 else text_frame.add_paragraph()
            )
            paragraph.text = bullet.text
            paragraph.level = bullet.level
            self._apply_font(
                paragraph,
                bullet.font,
                fallback=default_font,
            )
            self._apply_paragraph_style(
                paragraph,
                None,
                fallback=paragraph_style,
                preserve_level=True,
            )
