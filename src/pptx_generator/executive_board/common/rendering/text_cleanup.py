#!/usr/bin/env python3
from __future__ import annotations


def strip_bullet_prefix(text: str) -> str:
    if not text:
        return text
    return text[1:] if text.startswith("・") else text


def apply_strip_bullet_prefix(slide) -> None:
    for shape in slide.shapes:
        if not getattr(shape, "has_text_frame", False):
            continue
        text_frame = shape.text_frame
        for paragraph in text_frame.paragraphs:
            if paragraph.text:
                paragraph.text = strip_bullet_prefix(paragraph.text)
