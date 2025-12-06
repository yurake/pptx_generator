"""ステージごとのスライドコンテキスト生成ユーティリティ。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, List, Sequence

from pptx_generator.cli_handlers.prepare import slugify_prompt_layout

from .manager import SlideContext


def build_slide_key(index: int, layout: str | None, slide_id: str | None) -> str:
    slug_source = (layout or slide_id or f"slide{index:02}").strip()
    slug = slugify_prompt_layout(slug_source)
    return f"{index:02}_{slug}"


def slide_contexts_from_blueprint(
    slides: Sequence[Any],
    *,
    prompts_dir: Path | None = None,
) -> list[SlideContext]:
    contexts: list[SlideContext] = []
    for index, slide in enumerate(slides, start=1):
        layout = _coerce_str(slide.get("layout"))
        slide_id = _coerce_str(slide.get("slide_id"))
        key = build_slide_key(index, layout, slide_id)
        extra_env: dict[str, str] = {}
        required = slide.get("required")
        if isinstance(required, bool):
            extra_env["PPTX_SLIDE_REQUIRED"] = "1" if required else "0"
        intent_tags = slide.get("intent_tags")
        if isinstance(intent_tags, list):
            extra_env["PPTX_SLIDE_INTENT_TAGS"] = ",".join(
                str(tag).strip() for tag in intent_tags if str(tag).strip()
            )
        if prompts_dir is not None:
            prompt_path = prompts_dir / f"{key}.md"
            if prompt_path.exists():
                extra_env["PPTX_PROMPT_TEMPLATE_PATH"] = str(prompt_path.resolve())
        contexts.append(
            SlideContext(
                key=key,
                index=index,
                slide_id=slide_id,
                layout=layout,
                extra_env=extra_env,
            )
        )
    return contexts


def slide_contexts_from_generate_ready(path: Path) -> list[SlideContext]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

    slides = data.get("slides")
    if not isinstance(slides, Iterable):
        return []

    contexts: list[SlideContext] = []
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            continue
        layout_id = _coerce_str(slide.get("layout_id")) or _coerce_str(slide.get("layout_name"))
        meta = slide.get("meta")
        slide_id = None
        page_no = index
        if isinstance(meta, dict):
            slide_id = _coerce_str(meta.get("blueprint_slide_id")) or _coerce_str(
                meta.get("sources", [None])[0] if isinstance(meta.get("sources"), list) else None
            )
            if isinstance(meta.get("page_no"), int):
                page_no = meta["page_no"]
        key = build_slide_key(page_no, layout_id, slide_id)

        extra_env: dict[str, str] = {}
        if isinstance(meta, dict) and meta.get("page_no") is not None:
            extra_env["PPTX_SLIDE_PAGE_NO"] = str(meta.get("page_no"))
        contexts.append(
            SlideContext(
                key=key,
                index=page_no,
                slide_id=slide_id,
                layout=layout_id,
                extra_env=extra_env,
            )
        )

    # キーの重複や順序の乱れを避けるため、page_no でソートし直す
    contexts.sort(key=lambda item: (item.index, item.key))
    return contexts


def _coerce_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None
