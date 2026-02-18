from __future__ import annotations

import re
from typing import Any

PROMPT_TEMPLATE_FILENAME_PATTERN = re.compile(r"^(?P<index>\d{1,2})_(?P<slug>[a-z0-9-]+)\.md$", re.IGNORECASE)
PROMPT_USER_SECTION_START = "<<<user-editable:start"
PROMPT_USER_SECTION_END = "<<<user-editable:end"


def build_prompt_identifier(index: int, slide: Any) -> str:
    layout = getattr(slide, "layout", None)
    slide_id = getattr(slide, "slide_id", None)
    slug_source = layout or slide_id or f"slide{index:02}"
    slug = slugify_prompt_layout(str(slug_source))
    return f"{index:02}_{slug}"


def slugify_prompt_layout(source: str) -> str:
    lowered = source.strip().lower()
    if not lowered:
        lowered = "layout"
    normalized = re.sub(r"[^a-z0-9]+", "-", lowered)
    normalized = normalized.strip("-") or "layout"
    return normalized[:48]


__all__ = [
    "PROMPT_TEMPLATE_FILENAME_PATTERN",
    "PROMPT_USER_SECTION_START",
    "PROMPT_USER_SECTION_END",
    "build_prompt_identifier",
    "slugify_prompt_layout",
]
