"""Utilities for merging content and spec slide elements."""

from __future__ import annotations

import logging
from typing import Any, Mapping, Sequence

from ...models import ContentElements, ContentSlide, Slide, TemplateBlueprintSlot
from ...prepare.models import PrepareCard
from ...draft.draft_recommender import LayoutProfile
from ...utils.text_lines import split_lines_preserve_blank
from ..table_anchor import build_table_payload, is_table_payload, resolve_table_anchor

logger = logging.getLogger(__name__)


def merge_slide_elements(
    *,
    content_slide: ContentSlide | None,
    spec_slide: Slide | None,
    layout_profile: LayoutProfile | None,
) -> dict[str, Any]:
    base = convert_slide_elements(spec_slide) if spec_slide is not None else {}
    if content_slide is None or content_slide.elements is None:
        return base

    elements, table_payload = collect_content_elements(content_slide.elements, base)

    if spec_slide is not None:
        merge_spec_slide_details(
            elements=elements,
            base=base,
            spec_slide=spec_slide,
            table_payload=table_payload,
        )

    if table_payload is not None:
        apply_table_payload(
            elements=elements,
            base=base,
            table_payload=table_payload,
            spec_slide=spec_slide,
            layout_profile=layout_profile,
            content_slide=content_slide,
        )

    return elements


def collect_content_elements(
    content_elements: ContentElements, base: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    elements: dict[str, Any] = {}

    if content_elements.title:
        elements["title"] = content_elements.title

    if content_elements.subtitle:
        elements["subtitle"] = content_elements.subtitle

    if content_elements.body:
        elements["body"] = list(content_elements.body)
    elif "body" in base:
        elements["body"] = base["body"]

    if content_elements.note:
        elements["note"] = content_elements.note
    elif "note" in base:
        elements["note"] = base["note"]

    table_payload: dict[str, Any] | None = None
    if content_elements.table_data is not None:
        table_payload = build_table_payload(content_elements.table_data)

    return elements, table_payload


def merge_spec_slide_details(
    *,
    elements: dict[str, Any],
    base: dict[str, Any],
    spec_slide: Slide,
    table_payload: dict[str, Any] | None,
) -> None:
    if spec_slide.subtitle and "subtitle" not in elements:
        elements["subtitle"] = spec_slide.subtitle

    for key, value in base.items():
        if key in {"title", "body", "note", "subtitle"}:
            continue
        if table_payload is not None and is_table_payload(value):
            continue
        elements.setdefault(key, value)

    for anchor in spec_slide.auto_draw_anchors:
        elements.pop(anchor, None)


def apply_table_payload(
    *,
    elements: dict[str, Any],
    base: dict[str, Any],
    table_payload: dict[str, Any],
    spec_slide: Slide | None,
    layout_profile: LayoutProfile | None,
    content_slide: ContentSlide,
) -> None:
    placeholders = layout_profile.placeholders if layout_profile else ()
    anchor, reasons = resolve_table_anchor(spec_slide, placeholders)
    target_key = anchor or "table"

    if logger.isEnabledFor(logging.DEBUG):
        debug_reason = ", ".join(reasons) if reasons else "none"
        logger.debug(
            "table anchor resolved: slide_id=%s layout=%s anchor=%s reason=%s",
            getattr(content_slide, "id", "unknown"),
            layout_profile.layout_id if layout_profile else "unknown",
            target_key,
            debug_reason,
        )

    for key in list(elements.keys()):
        if key == target_key:
            continue
        if is_table_payload(elements[key]):
            elements.pop(key, None)

    if spec_slide is not None:
        for key, value in base.items():
            if key == target_key:
                continue
            if is_table_payload(value):
                elements.pop(key, None)

    elements[target_key] = table_payload


def convert_slide_elements(slide: Slide | None) -> dict[str, Any]:
    if slide is None:
        return {}
    elements: dict[str, Any] = {}
    if slide.title:
        elements["title"] = slide.title
    if slide.subtitle:
        elements["subtitle"] = slide.subtitle
    if slide.notes:
        elements["note"] = slide.notes

    body_lines: list[str] = []
    for group in slide.bullets:
        texts = [bullet.text for bullet in group.items]
        if not texts:
            continue
        if group.anchor:
            elements[group.anchor] = texts
        else:
            body_lines.extend(texts)
    if body_lines:
        elements["body"] = body_lines

    for index, table in enumerate(slide.tables, start=1):
        key = table.anchor or f"table_{index}"
        elements[key] = {
            "headers": table.columns,
            "rows": table.rows,
        }

    for index, image in enumerate(slide.images, start=1):
        key = image.anchor or f"image_{index}"
        elements[key] = {
            "source": str(image.source),
            "sizing": image.sizing,
        }

    for index, chart in enumerate(slide.charts, start=1):
        key = chart.anchor or f"chart_{index}"
        elements[key] = {
            "type": chart.type,
            "categories": chart.categories,
            "series": [series.model_dump(mode="json") for series in chart.series],
            "options": chart.options.model_dump(mode="json") if chart.options else None,
        }

    for index, textbox in enumerate(slide.textboxes, start=1):
        key = textbox.anchor or f"textbox_{index}"
        elements[key] = {"text": textbox.text}

    for anchor in slide.auto_draw_anchors:
        elements.pop(anchor, None)

    return elements


def card_to_lines(card: PrepareCard) -> list[str]:
    lines = list(card.iter_body_text())
    if not lines:
        headline = card.headline_or_title()
        if headline:
            lines.append(headline)
    return [line for line in lines if line]


def assign_slot_to_elements(
    elements: dict[str, Any],
    slot: TemplateBlueprintSlot,
    card: PrepareCard,
    lines: list[str],
) -> None:
    anchor = slot.anchor or slot.slot_id
    if not anchor:
        return
    anchor_lower = anchor.lower()
    if assign_special_anchor(elements, anchor_lower, card):
        return

    content_type = (slot.content_type or "text").lower()
    if content_type == "table":
        assign_table_content(elements, anchor, card, lines)
        return
    if content_type == "image":
        assign_image_content(elements, anchor, card, lines)
        return
    if content_type == "text":
        assign_text_content(elements, anchor, anchor_lower, card, lines)
        return


def assign_special_anchor(
    elements: dict[str, Any],
    anchor_lower: str,
    card: PrepareCard,
) -> bool:
    if anchor_lower in {"title", "main message"}:
        headline = card.headline_or_title()
        if headline:
            elements["title"] = headline
        return True
    if "subtitle" in anchor_lower:
        subtitle = card.subtitle_or_chapter() or card.headline_or_title()
        if subtitle:
            elements["subtitle"] = subtitle
        return True
    return False


def assign_table_content(
    elements: dict[str, Any],
    anchor: str,
    card: PrepareCard,
    lines: list[str],
) -> None:
    table_block = next(
        (block for block in card.content.body if block.type == "table"), None
    )
    if table_block and table_block.rows:
        elements[anchor] = {
            "headers": list(table_block.headers or []),
            "rows": [list(row) for row in table_block.rows],
        }
        return
    if lines:
        elements[anchor] = {
            "headers": ["項目"],
            "rows": [[line] for line in lines],
        }


def assign_image_content(
    elements: dict[str, Any],
    anchor: str,
    card: PrepareCard,
    lines: list[str],
) -> None:
    image_block = next(
        (block for block in card.content.body if block.type == "image"), None
    )
    if image_block and image_block.ref:
        if image_block.ref != anchor:
            elements[anchor] = {"source": image_block.ref}
            return
    if lines:
        elements[anchor] = lines


def assign_text_content(
    elements: dict[str, Any],
    anchor: str,
    anchor_lower: str,
    card: PrepareCard,
    lines: list[str],
) -> None:
    bullet_entries, paragraph_entries = extract_text_blocks(card)
    if bullet_entries:
        elements[anchor] = bullet_entries
        return
    if paragraph_entries:
        elements[anchor] = paragraph_entries
        return
    if lines:
        elements[anchor] = lines
        return
    if anchor_lower in {"body", "content"}:
        headline = card.headline_or_title()
        if headline:
            elements[anchor] = [headline]


def extract_text_blocks(card: PrepareCard) -> tuple[list[dict[str, Any]], list[str]]:
    bullet_entries: list[dict[str, Any]] = []
    paragraph_entries: list[str] = []
    for block in card.content.body:
        if block.type == "bullets" and block.data:
            append_bullet_entries(block.data.get("items"), bullet_entries)
            continue
        if isinstance(block.text, str):
            for line in split_lines_preserve_blank(block.text):
                stripped = line.strip()
                if stripped:
                    paragraph_entries.append(stripped)
                else:
                    paragraph_entries.append("")
    return bullet_entries, paragraph_entries


def append_bullet_entries(
    raw_items: Any,
    bullet_entries: list[dict[str, Any]],
) -> None:
    if not isinstance(raw_items, list):
        return
    for entry in raw_items:
        if isinstance(entry, dict):
            append_dict_bullet(entry, bullet_entries)
        elif isinstance(entry, str):
            text = entry.strip()
            if text:
                bullet_entries.append({"text": text, "level": 0})


def append_dict_bullet(
    entry: dict[str, Any],
    bullet_entries: list[dict[str, Any]],
) -> None:
    text = str(entry.get("text") or "").strip()
    if not text:
        return
    level_raw = entry.get("level", 0)
    try:
        level = max(int(level_raw), 0)
    except (TypeError, ValueError):
        level = 0
    bullet_entry: dict[str, Any] = {"text": text, "level": level}
    for key, value in entry.items():
        if key in {"text", "level"}:
            continue
        bullet_entry[key] = value
    bullet_entries.append(bullet_entry)


def merge_slide_notes(elements: dict[str, Any], note_lines: list[str]) -> None:
    if not note_lines:
        return
    aggregated_notes = "\n".join(note_lines)
    existing_note = elements.get("note")
    if isinstance(existing_note, str) and existing_note.strip():
        aggregated_notes = f"{existing_note.rstrip()}\n{aggregated_notes}"
    elements["note"] = aggregated_notes
