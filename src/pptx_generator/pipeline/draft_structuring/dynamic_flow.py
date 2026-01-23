from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from ...draft.draft_intel import summarize_analyzer_counts
from ...draft.draft_recommender import CardLayoutRecommender, LayoutProfile
from ...models import (
    ContentApprovalDocument,
    ContentSlide,
    DraftAnalyzerSummary,
    DraftDocument,
    DraftMeta,
    DraftSection,
    DraftSlideCard,
    JobSpec,
    Slide,
)
from ...utils.usage_tags import get_usage_tag_detail_map
from .types import (
    DraftAccumulator,
    DraftStructuringOptions,
    DraftWorkItem,
    card_slot_fulfilled,
    card_slot_id,
)

logger = logging.getLogger(__name__)


def build_dynamic_document(
    *,
    options: DraftStructuringOptions,
    spec: JobSpec,
    document: ContentApprovalDocument,
    layouts: Sequence[LayoutProfile],
    analyzer_map: dict[str, DraftAnalyzerSummary],
    recommender: CardLayoutRecommender,
    dynamic_prepare: bool,
) -> tuple[DraftDocument, list[dict[str, Any]], dict[str, Any]]:
    spec_lookup = {slide.id: slide for slide in spec.slides}
    layout_lookup = {profile.layout_id: profile for profile in layouts}
    tag_detail_map = get_usage_tag_detail_map()

    accumulator = DraftAccumulator()
    work_items = _build_work_items(
        document=document,
        spec=spec,
        spec_lookup=spec_lookup,
        dynamic_prepare=dynamic_prepare,
    )

    for item in work_items:
        _process_work_item(
            options=options,
            item=item,
            accumulator=accumulator,
            analyzer_map=analyzer_map,
            recommender=recommender,
            layout_lookup=layout_lookup,
            tag_detail_map=tag_detail_map,
            layouts=layouts,
        )

    draft_document = _finalize_draft_document(
        options=options,
        accumulator=accumulator,
        analyzer_map=analyzer_map,
        spec=spec,
    )

    if logger.isEnabledFor(logging.INFO):
        logger.info(
            "layout recommendation summary: invoked=%d used=%d simulated=%d",
            accumulator.ai_summary["invoked"],
            accumulator.ai_summary["used"],
            accumulator.ai_summary["simulated"],
        )

    return draft_document, accumulator.mapping_logs, accumulator.ai_summary


def _build_work_items(
    *,
    document: ContentApprovalDocument,
    spec: JobSpec,
    spec_lookup: dict[str, Slide],
    dynamic_prepare: bool,
) -> list[DraftWorkItem]:
    if dynamic_prepare:
        return [
            DraftWorkItem(
                content_slide=content_slide,
                spec_slide=spec_lookup.get(content_slide.id),
            )
            for content_slide in document.slides
        ]

    slides_by_id = {slide.id: slide for slide in document.slides}
    return [
        DraftWorkItem(
            content_slide=slides_by_id.get(spec_slide.id),
            spec_slide=spec_slide,
        )
        for spec_slide in spec.slides
    ]


def _process_work_item(
    *,
    options: DraftStructuringOptions,
    item: DraftWorkItem,
    accumulator: DraftAccumulator,
    analyzer_map: dict[str, DraftAnalyzerSummary],
    recommender: CardLayoutRecommender,
    layout_lookup: Mapping[str, LayoutProfile],
    tag_detail_map: Mapping[str, Any],
    layouts: Sequence[LayoutProfile],
) -> None:
    content_slide = item.content_slide
    spec_slide = item.spec_slide
    if content_slide is None:
        return

    section = _ensure_section(accumulator, content_slide, spec_slide)
    card_order = len(section.slides) + 1
    analyzer_summary = analyzer_map.get(content_slide.id)
    preferred_layout = (
        spec_slide.layout
        if spec_slide is not None and getattr(spec_slide, "layout", None)
        else content_slide.type_hint
    ) or "Content"

    recommendation, card = _build_card(
        content_slide,
        preferred_layout,
        layouts,
        order=card_order,
        analyzer_summary=analyzer_summary,
        recommender=recommender,
    )
    section.slides.append(card)

    selected_layout = card.layout_hint
    ai_used = _update_ai_summary(
        accumulator,
        recommendation,
        selected_layout,
        options,
        preferred_layout,
        content_slide.id,
    )
    mapping_entry = _build_mapping_entry(
        content_slide=content_slide,
        preferred_layout=preferred_layout,
        selected_layout=selected_layout,
        recommendation=recommendation,
        layout_lookup=layout_lookup,
        tag_detail_map=tag_detail_map,
        ai_used=ai_used,
    )
    accumulator.mapping_logs.append(mapping_entry)


def _finalize_draft_document(
    *,
    options: DraftStructuringOptions,
    accumulator: DraftAccumulator,
    analyzer_map: dict[str, DraftAnalyzerSummary],
    spec: JobSpec,
) -> DraftDocument:
    sections = accumulator.sections
    meta = DraftMeta(
        target_length=options.target_length or sum(len(section.slides) for section in sections),
        structure_pattern=options.structure_pattern or "custom",
        appendix_limit=options.appendix_limit,
    )

    if analyzer_map:
        meta.analyzer_summary = summarize_analyzer_counts(analyzer_map.values())

    return DraftDocument(sections=sections, meta=meta)


def _resolve_section(content_slide: ContentSlide, spec_slide: Slide | None) -> tuple[str, str]:
    def _normalize_value(value: Any | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _story_value(field: str) -> str | None:
        story = getattr(content_slide, "story", None)
        if story is None:
            return None
        raw = story.get(field) if isinstance(story, dict) else getattr(story, field, None)
        return _normalize_value(raw)

    chapter_id = _story_value("chapter_id")
    phase = _story_value("phase")
    angle = _story_value("angle")

    if chapter_id:
        section_name = angle or phase or f"Chapter {chapter_id}"
        return chapter_id, section_name
    if phase:
        section_name = angle or f"Phase {phase}"
        return phase, section_name

    intent = _normalize_value(content_slide.intent)
    if intent:
        return intent, f"Intent: {intent}"

    layout = getattr(spec_slide, "layout", None)
    layout_value = _normalize_value(layout)
    if layout_value:
        return layout_value, f"Layout: {layout_value}"

    slide_id = _normalize_value(content_slide.id) or "untitled"
    return slide_id, f"Slide: {slide_id}"


def _ensure_section(
    accumulator: DraftAccumulator,
    content_slide: ContentSlide,
    spec_slide: Slide | None,
) -> DraftSection:
    section_key, section_name = _resolve_section(content_slide, spec_slide)
    section = accumulator.section_map.get(section_key)
    if section is not None:
        return section
    section = DraftSection(
        name=section_name,
        order=len(accumulator.section_map) + 1,
        status="draft",
    )
    accumulator.section_map[section_key] = section
    accumulator.sections.append(section)
    return section


def _build_card(
    content_slide: ContentSlide,
    default_layout: str,
    layouts: Sequence[LayoutProfile],
    *,
    order: int,
    analyzer_summary: DraftAnalyzerSummary | None,
    recommender: CardLayoutRecommender,
) -> tuple[Any, DraftSlideCard]:
    recommendation = recommender.recommend(
        slide=content_slide,
        preferred_layout=default_layout,
        layouts=layouts,
        analyzer_summary=analyzer_summary,
    )
    candidates = recommendation.candidates
    layout_hint = candidates[0][0].layout_id if candidates else default_layout
    layout_detail = candidates[0][1] if candidates else None

    card = DraftSlideCard(
        ref_id=content_slide.id,
        order=order,
        layout_hint=layout_hint,
        locked=False,
        status="draft",
        layout_candidates=[candidate for candidate, _ in candidates[:5]],
        appendix=False,
        layout_score_detail=layout_detail,
        analyzer_summary=analyzer_summary,
    )
    return recommendation, card


def _update_ai_summary(
    accumulator: DraftAccumulator,
    recommendation: Any,
    selected_layout: str,
    options: DraftStructuringOptions,
    preferred_layout: str,
    slide_id: str,
) -> bool:
    ai_scores = recommendation.ai_scores
    ai_used = selected_layout in ai_scores and ai_scores[selected_layout] > 0.0
    if ai_used:
        accumulator.ai_summary["used"] += 1

    ai_response = recommendation.ai_response
    simulated = False

    if ai_response is not None:
        accumulator.ai_summary["invoked"] += 1
        model = ai_response.model or "unknown"
        models = accumulator.ai_summary["models"]
        models[model] = models.get(model, 0) + 1
    elif (
        options.enable_ai_recommender
        and options.enable_ai_simulation
        and options.ai_weight > 0
        and not ai_scores
        and _has_positive_ai_recommendation(recommendation.candidates)
    ):
        accumulator.ai_summary["simulated"] += 1
        simulated = True
        if logger.isEnabledFor(logging.INFO):
            logger.info(
                "layout AI simulated: slide_id=%s preferred=%s",
                slide_id,
                preferred_layout,
            )
    return ai_used or simulated


def _build_mapping_entry(
    *,
    content_slide: ContentSlide,
    preferred_layout: str,
    selected_layout: str,
    recommendation: Any,
    layout_lookup: Mapping[str, LayoutProfile],
    tag_detail_map: Mapping[str, Any],
    ai_used: bool,
) -> dict[str, Any]:
    candidate_logs = _serialize_candidates(recommendation, layout_lookup, tag_detail_map)
    source_payload = (
        content_slide.source.model_dump(mode="json")
        if content_slide.source is not None
        else None
    )
    ai_response_payload = _serialize_ai_response(recommendation.ai_response)

    mapping_entry: dict[str, Any] = {
        "slide_id": content_slide.id,
        "preferred_layout": preferred_layout,
        "selected_layout": selected_layout,
        "ai_recommendation_used": ai_used,
        "candidates": candidate_logs,
        "ai_response": ai_response_payload,
        "source": source_payload,
    }

    selected_profile = layout_lookup.get(selected_layout)
    if selected_profile:
        if selected_profile.meta and selected_profile.meta.get("heuristic_reason"):
            mapping_entry["heuristic_reason"] = selected_profile.meta["heuristic_reason"]
        if selected_profile.blueprint:
            mapping_entry["selected_blueprint"] = selected_profile.blueprint
        selected_usage_details = {
            tag: tag_detail_map[tag]
            for tag in sorted(set(selected_profile.usage_tags or ()))
            if tag in tag_detail_map
        }
        if selected_usage_details:
            mapping_entry["selected_usage_tags_detail"] = selected_usage_details
    return mapping_entry


def _serialize_candidates(
    recommendation: Any,
    layout_lookup: Mapping[str, LayoutProfile],
    tag_detail_map: Mapping[str, Any],
) -> list[dict[str, Any]]:
    candidate_logs: list[dict[str, Any]] = []
    for candidate, detail in recommendation.candidates:
        layout_id = candidate.layout_id
        entry: dict[str, Any] = {
            "layout_id": layout_id,
            "score": candidate.score,
            "ai_score": recommendation.ai_scores.get(layout_id, 0.0),
            "usage_tags_rule": list(recommendation.baseline_tags.get(layout_id, ())),
            "ai_tags": list(recommendation.classified_tags.get(layout_id, ())),
            "effective_usage_tags": list(recommendation.effective_tags.get(layout_id, ())),
            "unknown_ai_tags": list(recommendation.ai_unknown_tags.get(layout_id, ())),
            "detail": {
                "uses_tag": detail.uses_tag,
                "content_capacity": detail.content_capacity,
                "diversity": detail.diversity,
                "analyzer_support": detail.analyzer_support,
                "ai_recommendation": detail.ai_recommendation,
            },
        }
        profile = layout_lookup.get(layout_id)
        tags_for_detail: set[str] = set(recommendation.baseline_tags.get(layout_id, ()))
        tags_for_detail.update(recommendation.classified_tags.get(layout_id, ()))
        tags_for_detail.update(recommendation.effective_tags.get(layout_id, ()))
        if recommendation.ai_unknown_tags.get(layout_id):
            tags_for_detail.update(recommendation.ai_unknown_tags[layout_id])
        if profile:
            tags_for_detail.update(profile.usage_tags or ())
            if profile.placeholder_summary:
                entry["placeholder_summary"] = profile.placeholder_summary
            if profile.heuristic:
                entry["heuristic"] = profile.heuristic
            if profile.blueprint:
                entry["blueprint"] = profile.blueprint
            if profile.meta:
                entry["meta"] = profile.meta
        usage_tag_details = {
            tag: tag_detail_map[tag]
            for tag in sorted(tags_for_detail)
            if tag in tag_detail_map
        }
        if usage_tag_details:
            entry["usage_tags_detail"] = usage_tag_details
        candidate_logs.append(entry)
    return candidate_logs


def _serialize_ai_response(response: Any) -> dict[str, Any] | None:
    if response is None:
        return None
    payload = {
        "model": response.model,
        "recommended": response.recommended,
        "reasons": response.reasons,
        "classifications": {key: list(value) for key, value in response.classifications.items()},
    }
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            (
                "layout AI response: model=%s recommended=%s "
                "reasons=%s classifications=%s"
            ),
            response.model,
            response.recommended,
            response.reasons,
            response.classifications,
        )
    return payload


def _has_positive_ai_recommendation(
    candidates: Sequence[tuple[Any, Any]],
) -> bool:
    return any(detail.ai_recommendation > 0.0 for _, detail in candidates)
