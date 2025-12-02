"""マッピング処理のためのワークアイテム構築。"""

from __future__ import annotations

from typing import Sequence

from ...models import ContentSlide, DraftDocument, DraftSlideCard, Slide
from .types import MappingWorkItem


def build_section_lookup(draft_document: DraftDocument) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for section in draft_document.sections:
        for card in section.slides:
            lookup[card.ref_id] = section.name
    return lookup


def build_card_lookup(draft_document: DraftDocument) -> dict[str, DraftSlideCard]:
    lookup: dict[str, DraftSlideCard] = {}
    for section in draft_document.sections:
        for card in section.slides:
            lookup[card.ref_id] = card
    return lookup


def build_work_items(
    *,
    draft_document: DraftDocument,
    section_lookup: dict[str, str],
    card_lookup: dict[str, DraftSlideCard],
    content_lookup: dict[str, ContentSlide],
    spec_lookup: dict[str, Slide],
    spec_slides: Sequence[Slide],
) -> list[MappingWorkItem]:
    ordered_cards: list[tuple[str | None, DraftSlideCard]] = []
    for section in draft_document.sections:
        for card in section.slides:
            ordered_cards.append((section.name, card))

    if ordered_cards:
        return [
            MappingWorkItem(
                page_no=index,
                section_name=section_name,
                spec_slide=spec_lookup.get(card.ref_id),
                card=card,
                content_slide=content_lookup.get(card.ref_id),
            )
            for index, (section_name, card) in enumerate(ordered_cards, start=1)
        ]

    items: list[MappingWorkItem] = []
    for index, spec_slide in enumerate(spec_slides, start=1):
        items.append(
            MappingWorkItem(
                page_no=index,
                section_name=section_lookup.get(spec_slide.id),
                spec_slide=spec_slide,
                card=card_lookup.get(spec_slide.id),
                content_slide=content_lookup.get(spec_slide.id),
            )
        )
    return items
