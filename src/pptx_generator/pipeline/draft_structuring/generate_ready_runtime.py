"""Helpers for building generate-ready documents and metadata."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, TYPE_CHECKING

from ...models import (
    ContentApprovalDocument,
    ContentSlide,
    DraftDocument,
    DraftSlideCard,
    GenerateReadyDocument,
    GenerateReadyMeta,
    GenerateReadySlide,
    JobAuth,
    JobMeta,
    JobSpec,
    MappingSlideMeta,
    Slide,
)
from .slide_elements import convert_slide_elements, merge_slide_elements

logger = logging.getLogger(__name__)


def _build_auto_draw_payload(spec_slide: Slide) -> list[dict[str, float | str]]:
    return [
        {
            "anchor": anchor,
            "left_in": box.left_in,
            "top_in": box.top_in,
            "width_in": box.width_in,
            "height_in": box.height_in,
        }
        for anchor, box in spec_slide.auto_draw_boxes.items()
    ]


def _build_generate_ready_meta(
    *,
    draft: DraftDocument,
    spec: JobSpec,
    template_path: Path | None,
    content_hash: str | None,
) -> GenerateReadyMeta:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = GenerateReadyMeta(
        template_version=draft.meta.template_id,
        template_path=str(template_path) if template_path else getattr(spec.meta, "template_path", None),
        content_hash=content_hash,
        generated_at=timestamp,
        job_meta=spec.meta if isinstance(spec.meta, JobMeta) else JobMeta.model_validate(spec.meta.model_dump()),
        job_auth=spec.auth if isinstance(spec.auth, JobAuth) else JobAuth.model_validate(spec.auth.model_dump()),
    )
    if meta.template_path is None and getattr(spec.meta, "template_path", None):
        meta.template_path = getattr(spec.meta, "template_path", None)
    return meta


def build_generate_ready_document(
    *,
    step: "DraftStructuringStep",
    spec: JobSpec,
    draft: DraftDocument,
    content_document: ContentApprovalDocument | None,
    template_path: Path | None = None,
) -> GenerateReadyDocument:
    section_lookup: Dict[str, str] = {}
    cards_in_order: List[DraftSlideCard] = []
    for section in draft.sections:
        for card in section.slides:
            section_lookup[card.ref_id] = section.name
            cards_in_order.append(card)

    spec_lookup = {slide.id: slide for slide in spec.slides}
    content_lookup: Dict[str, ContentSlide] = {}
    content_hash: Optional[str] = None
    if content_document is not None:
        content_lookup = {slide.id: slide for slide in content_document.slides}
        try:
            payload = content_document.model_dump(mode="json")
            digest = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            content_hash = hashlib.sha256(digest.encode("utf-8")).hexdigest()
        except (TypeError, ValueError) as exc:
            logger.debug("content_approved のハッシュ化に失敗しました: %s", exc)

    slides: List[GenerateReadySlide] = []
    if not cards_in_order:
        return _build_empty_generate_ready(
            spec=spec,
            draft=draft,
            template_path=template_path,
            content_hash=content_hash,
            layout_name_lookup=step._layout_name_lookup,
        )

    for index, card in enumerate(cards_in_order, start=1):
        spec_slide = spec_lookup.get(card.ref_id)
        section_name = section_lookup.get(card.ref_id)
        content_slide = content_lookup.get(card.ref_id)
        layout_id = card.layout_hint
        if not layout_id and spec_slide is not None:
            layout_id = spec_slide.layout
        layout_id = layout_id or "title"
        layout_name = step._layout_name_lookup.get(layout_id)
        if layout_name is None and spec_slide is not None and spec_slide.layout == layout_id:
            layout_name = spec_slide.layout
        if layout_name is None:
            layout_name = layout_id
        layout_profile = step._layout_catalog.get(layout_id)
        elements = merge_slide_elements(
            content_slide=content_slide,
            spec_slide=spec_slide,
            layout_profile=layout_profile,
        )
        sources = [spec_slide.id] if spec_slide is not None else [card.ref_id]
        auto_draw_payload = []
        if spec_slide is not None:
            auto_draw_payload = _build_auto_draw_payload(spec_slide)
        slides.append(
            GenerateReadySlide(
                layout_id=layout_id,
                layout_name=layout_name,
                elements=elements,
                meta=MappingSlideMeta(
                    section=section_name,
                    page_no=index,
                    sources=sources,
                    fallback="none",
                    auto_draw=auto_draw_payload,
                ),
            )
        )

    meta = _build_generate_ready_meta(
        draft=draft,
        spec=spec,
        template_path=template_path,
        content_hash=content_hash,
    )
    return GenerateReadyDocument(slides=slides, meta=meta)


def build_generate_ready_meta_payload(
    *,
    draft: DraftDocument,
    generate_ready: GenerateReadyDocument,
    ai_summary: dict[str, Any],
    alignment_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sections_payload, main_slides_total, appendix_slides_total = summarize_sections(draft)
    template_info = build_template_info(draft)
    statistics = build_statistics_block(
        generate_ready=generate_ready,
        main_slides=main_slides_total,
        appendix_slides=appendix_slides_total,
        ai_summary=ai_summary,
    )

    payload = {
        "generated_at": generate_ready.meta.generated_at,
        "sections": sections_payload,
        "statistics": statistics,
        "template": template_info,
        "analyzer_summary": draft.meta.analyzer_summary,
        "return_reason_stats": draft.meta.return_reason_stats,
        "ai_recommendation": build_ai_recommendation_block(ai_summary),
    }
    if alignment_payload:
        payload["slide_alignment"] = alignment_payload
    apply_optional_generate_ready_meta(
        payload=payload,
        generate_ready=generate_ready,
    )
    return payload


def summarize_sections(draft: DraftDocument) -> Tuple[List[dict[str, Any]], int, int]:
    sections_payload: List[dict[str, Any]] = []
    main_total = 0
    appendix_total = 0

    for section in draft.sections:
        main_count = sum(1 for card in section.slides if not card.appendix)
        appendix_count = sum(1 for card in section.slides if card.appendix)
        main_total += main_count
        appendix_total += appendix_count
        sections_payload.append(
            {
                "name": section.name,
                "order": section.order,
                "status": section.status,
                "slides": len(section.slides),
                "main_slides": main_count,
                "appendix_slides": appendix_count,
                "locked": any(card.locked for card in section.slides),
            }
        )

    return sections_payload, main_total, appendix_total


def build_template_info(draft: DraftDocument) -> dict[str, Any]:
    return {
        "template_id": draft.meta.template_id,
        "structure_pattern": draft.meta.structure_pattern,
        "target_length": draft.meta.target_length,
        "appendix_limit": draft.meta.appendix_limit,
        "match_score": draft.meta.template_match_score,
        "mismatch": [item.model_dump(mode="json") for item in draft.meta.template_mismatch],
    }


def build_ai_recommendation_block(ai_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "invoked": ai_summary.get("invoked", 0),
        "used": ai_summary.get("used", 0),
        "simulated": ai_summary.get("simulated", 0),
        "models": ai_summary.get("models", {}),
    }


def build_statistics_block(
    *,
    generate_ready: GenerateReadyDocument,
    main_slides: int,
    appendix_slides: int,
    ai_summary: dict[str, Any],
) -> dict[str, Any]:
    statistics = {
        "total_slides": len(generate_ready.slides),
        "main_slides": main_slides,
        "appendix_slides": appendix_slides,
        "ai_recommendation_used": ai_summary.get("used", 0),
    }
    return statistics


def apply_optional_generate_ready_meta(
    *,
    payload: dict[str, Any],
    generate_ready: GenerateReadyDocument,
) -> None:
    payload["mode"] = generate_ready.meta.layout_mode
    if generate_ready.meta.slot_summary:
        payload["slot_summary"] = generate_ready.meta.slot_summary
    if generate_ready.meta.blueprint_path:
        payload["blueprint_path"] = generate_ready.meta.blueprint_path
    if generate_ready.meta.blueprint_hash:
        payload["blueprint_hash"] = generate_ready.meta.blueprint_hash


def _build_empty_generate_ready(
    *,
    spec: JobSpec,
    draft: DraftDocument,
    template_path: Path | None,
    content_hash: str | None,
    layout_name_lookup: Mapping[str, str],
) -> GenerateReadyDocument:
    slides: List[GenerateReadySlide] = []
    for index, spec_slide in enumerate(spec.slides, start=1):
        layout_name = layout_name_lookup.get(spec_slide.layout, spec_slide.layout)
        auto_draw_payload = _build_auto_draw_payload(spec_slide)
        slides.append(
            GenerateReadySlide(
                layout_id=spec_slide.layout,
                layout_name=layout_name,
                elements=convert_slide_elements(spec_slide),
                meta=MappingSlideMeta(
                    section=None,
                    page_no=index,
                    sources=[spec_slide.id],
                    fallback="none",
                    auto_draw=auto_draw_payload,
                ),
            )
        )

    meta = _build_generate_ready_meta(
        draft=draft,
        spec=spec,
        template_path=template_path,
        content_hash=content_hash,
    )
    return GenerateReadyDocument(slides=slides, meta=meta)


# Circular import guard.
if TYPE_CHECKING:  # pragma: no cover
    from .step import DraftStructuringStep
