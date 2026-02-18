"""Helpers for the static draft structuring flow."""

from __future__ import annotations

import logging
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, List, Mapping, Sequence, Tuple

from ...stages.prepare.data_models import PrepareCard, PrepareDocument, PrepareGenerationMeta
from ...models import (
    ContentApprovalDocument,
    DraftDocument,
    DraftLayoutCandidate,
    DraftMeta,
    DraftSection,
    DraftSlideCard,
    GenerateReadyDocument,
    GenerateReadyMeta,
    GenerateReadySlide,
    JobAuth,
    JobMeta,
    JobSpec,
    MappingCandidate,
    MappingFallbackState,
    MappingLog,
    MappingLogMeta,
    MappingLogSlide,
    MappingSlideMeta,
    TemplateBlueprint,
    TemplateSpec,
    Slide,
)
from ..base import PipelineContext
from ...api.draft_store import DraftStore, BoardAlreadyExistsError
from .errors import DraftStructuringError
from .types import DraftStructuringOptions, StaticArtifacts, card_slot_fulfilled, card_slot_id
from .slide_elements import assign_slot_to_elements, merge_slide_notes, card_to_lines
from .generate_ready_runtime import build_generate_ready_meta_payload

if TYPE_CHECKING:  # pragma: no cover - typing only.
    from .step import DraftStructuringStep

logger = logging.getLogger(__name__)


def run_static_mode(
    *,
    step: "DraftStructuringStep",
    context: PipelineContext,
    content_document: ContentApprovalDocument,
    prepare_meta: PrepareGenerationMeta,
) -> None:
    prepare_document = context.artifacts.get("prepare_document")
    if not isinstance(prepare_document, PrepareDocument):
        msg = "static モードでは prepare_document が必要です"
        raise DraftStructuringError(msg)

    template_spec_path = resolve_static_template_spec_path(step.options, context, prepare_meta)
    template_spec = step._load_template_spec(template_spec_path)
    validate_static_template_spec(step, template_spec, prepare_meta)

    step._layout_name_lookup = {layout.name: layout.name for layout in template_spec.layouts}

    artifacts = build_static_artifacts(
        step=step,
        spec=context.spec,
        prepare_document=prepare_document,
        content_document=content_document,
        template_spec=template_spec,
        prepare_meta=prepare_meta,
    )

    write_static_outputs(step=step, context=context, artifacts=artifacts)


def resolve_static_template_spec_path(
    options: DraftStructuringOptions,
    context: PipelineContext,
    prepare_meta: PrepareGenerationMeta,
) -> Path:
    spec_source_path = Path(options.spec_source_path) if options.spec_source_path else None
    template_spec_meta = getattr(context.spec.meta, "template_spec_path", None)
    candidate: Path | None = None

    if template_spec_meta:
        candidate = Path(template_spec_meta)
        if not candidate.is_absolute():
            if spec_source_path is not None:
                candidate = (spec_source_path.parent / candidate).resolve()
            else:
                candidate = candidate.resolve()

    if candidate is None and prepare_meta.blueprint_path:
        blueprint_path = Path(prepare_meta.blueprint_path)
        candidate = blueprint_path.resolve() if not blueprint_path.is_absolute() else blueprint_path

    if candidate is None:
        msg = "template_spec のパスを jobspec または ai_generation_meta から取得できませんでした"
        raise DraftStructuringError(msg)

    if not candidate.exists():
        msg = f"template_spec が見つかりません: {candidate}"
        raise DraftStructuringError(msg)

    return candidate


def validate_static_template_spec(
    step: "DraftStructuringStep",
    template_spec: TemplateSpec,
    prepare_meta: PrepareGenerationMeta,
) -> None:
    if template_spec.layout_mode != "static" or template_spec.blueprint is None:
        msg = "template_spec が static Blueprint を含んでいません"
        raise DraftStructuringError(msg)

    meta_source = getattr(prepare_meta, "template_source", "template")
    if meta_source != template_spec.template_source:
        msg = "template_spec と ai_generation_meta の template_source が一致しません"
        raise DraftStructuringError(msg)

    if prepare_meta.blueprint_hash:
        computed_hash = step._compute_blueprint_hash(template_spec.blueprint)
        if prepare_meta.blueprint_hash != computed_hash:
            msg = "Blueprint ハッシュが ai_generation_meta と一致しません"
            raise DraftStructuringError(msg)


def write_static_outputs(
    *,
    step: "DraftStructuringStep",
    context: PipelineContext,
    artifacts: StaticArtifacts,
) -> None:
    output_dir = step.options.output_dir or context.workdir
    output_dir.mkdir(parents=True, exist_ok=True)

    draft_path = output_dir / step.options.draft_filename
    approved_path = output_dir / step.options.approved_filename
    log_path = output_dir / step.options.log_filename
    mapping_log_path = output_dir / step.options.mapping_log_filename

    step._write_document(draft_path, artifacts.draft)
    step._write_document(approved_path, artifacts.draft)
    step._write_log(log_path, [])
    step._write_json(mapping_log_path, artifacts.mapping_log)

    ready_path = output_dir / step.options.generate_ready_filename
    step._write_json(
        ready_path,
        artifacts.generate_ready.model_dump(mode="json", exclude_none=True),
    )
    context.add_artifact("generate_ready", artifacts.generate_ready)
    context.add_artifact("generate_ready_path", str(ready_path))

    ready_meta_payload = build_generate_ready_meta_payload(
        draft=artifacts.draft,
        generate_ready=artifacts.generate_ready,
        ai_summary=artifacts.ai_summary,
    )
    ready_meta_path = output_dir / step.options.generate_ready_meta_filename
    step._write_json(ready_meta_path, ready_meta_payload)
    context.add_artifact("generate_ready_meta_path", str(ready_meta_path))

    context.add_artifact("draft_document", artifacts.draft)
    context.add_artifact("draft_document_path", str(approved_path))
    context.add_artifact("draft_review_log_path", str(log_path))
    context.add_artifact("draft_mapping_log_path", str(mapping_log_path))

    spec_id = step._spec_id_from_title(getattr(context.spec.meta, "title", None))
    context.add_artifact("draft_spec_id", spec_id)

    store_dir = step.options.draft_store_dir
    store = DraftStore(base_dir=store_dir if store_dir is not None else None)
    try:
        store.create_board(spec_id, artifacts.draft)
    except BoardAlreadyExistsError:
        store.overwrite_board(spec_id, artifacts.draft)

    logger.info(
        "Static テンプレート向け Draft ドキュメントを生成しました: slides=%d",
        sum(len(section.slides) for section in artifacts.draft.sections),
    )


def build_static_artifacts(
    *,
    step: "DraftStructuringStep",
    spec: JobSpec,
    prepare_document: PrepareDocument,
    content_document: ContentApprovalDocument,
    template_spec: TemplateSpec,
    prepare_meta: PrepareGenerationMeta,
) -> StaticArtifacts:
    blueprint: TemplateBlueprint = template_spec.blueprint  # type: ignore[assignment]

    cards_by_slot = build_cards_by_slot(prepare_document)
    spec_lookup = {slide.id: slide for slide in spec.slides}

    slot_summary, unused_slots, blueprint_slot_ids = compute_static_slot_stats(
        step.options,
        blueprint=blueprint,
        cards_by_slot=cards_by_slot,
    )
    orphan_cards = collect_orphan_cards(prepare_document.cards, blueprint_slot_ids)

    sections, generate_ready_slides, mapping_slides = build_static_slides(
        step=step,
        blueprint=blueprint,
        spec_lookup=spec_lookup,
        cards_by_slot=cards_by_slot,
        layout_lookup=step._layout_name_lookup,
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content_hash = step._compute_content_hash(content_document)

    generate_ready = GenerateReadyDocument(
        slides=generate_ready_slides,
        meta=GenerateReadyMeta(
            template_version=None,
            template_id=getattr(spec.meta, "template_id", None),
            template_path=None,
            content_hash=content_hash,
            generated_at=timestamp,
            job_meta=spec.meta if isinstance(spec.meta, JobMeta) else JobMeta.model_validate(spec.meta.model_dump()),
            job_auth=spec.auth if isinstance(spec.auth, JobAuth) else JobAuth.model_validate(spec.auth.model_dump()),
            layout_mode="static",
            blueprint_path=prepare_meta.blueprint_path,
            blueprint_hash=prepare_meta.blueprint_hash,
            slot_summary=slot_summary,
            template_source=prepare_meta.template_source,
        ),
    )

    draft_meta = DraftMeta(
        target_length=len(blueprint.slides),
        structure_pattern="static",
        appendix_limit=step.options.appendix_limit,
        template_id=template_spec.template_path,
        template_match_score=1.0,
        template_mismatch=[],
        return_reason_stats={},
        analyzer_summary={},
    )
    draft = DraftDocument(sections=sections, meta=draft_meta)

    blueprint_path_value = prepare_meta.blueprint_path or getattr(spec.meta, "template_spec_path", None)

    mapping_log_meta = MappingLogMeta(
        mapping_time_ms=0,
        fallback_count=0,
        ai_patch_count=0,
        analyzer_issue_count=0,
        mode="static",
        blueprint_path=str(blueprint_path_value) if blueprint_path_value else None,
        slot_summary=slot_summary,
        static_slot_checks={
            "unused_slots": unused_slots,
            "orphan_cards": orphan_cards,
        },
    )
    mapping_log = MappingLog(slides=mapping_slides, meta=mapping_log_meta).model_dump(mode="json")

    ai_summary = {
        "mode": "static",
        "invoked": 0,
        "used": 0,
        "simulated": 0,
        "models": {},
    }

    return StaticArtifacts(
        draft=draft,
        generate_ready=generate_ready,
        mapping_log=mapping_log,
        ai_summary=ai_summary,
        slot_summary=slot_summary,
    )


def build_cards_by_slot(prepare_document: PrepareDocument) -> dict[str, PrepareCard]:
    cards_by_slot: dict[str, PrepareCard] = {}
    for card in prepare_document.cards:
        slot_id = card_slot_id(card)
        if slot_id:
            cards_by_slot[slot_id] = card
    return cards_by_slot


def compute_static_slot_stats(
    options: DraftStructuringOptions,
    *,
    blueprint: TemplateBlueprint,
    cards_by_slot: Mapping[str, PrepareCard],
) -> tuple[dict[str, int], list[str], set[str]]:
    total_slots = 0
    required_total = 0
    required_fulfilled = 0
    optional_used = 0
    unused_slots: list[str] = []
    blueprint_slot_ids: set[str] = set()

    for blueprint_slide in blueprint.slides:
        for slot in blueprint_slide.slots:
            blueprint_slot_ids.add(slot.slot_id)
            total_slots += 1
            card = cards_by_slot.get(slot.slot_id)
            has_default = bool(slot.default_text or slot.default_payload)
            if slot.required:
                required_total += 1
                if card_slot_fulfilled(card) or has_default:
                    required_fulfilled += 1
            else:
                if card_slot_fulfilled(card):
                    optional_used += 1
                elif not has_default:
                    unused_slots.append(slot.slot_id)

    if required_fulfilled < required_total:
        missing = required_total - required_fulfilled
        msg = f"必須 slot に対応するカードが不足しています: missing={missing}"
        raise DraftStructuringError(msg)

    slot_summary = {
        "required_total": required_total,
        "required_fulfilled": required_fulfilled,
        "optional_total": total_slots - required_total,
        "optional_used": optional_used,
    }

    return slot_summary, unused_slots, blueprint_slot_ids


def collect_orphan_cards(
    cards: Sequence[PrepareCard], blueprint_slot_ids: set[str]
) -> list[str]:
    orphan_cards: list[str] = []
    for card in cards:
        slot_id = card_slot_id(card)
        if slot_id and slot_id not in blueprint_slot_ids:
            orphan_cards.append(slot_id)
    return orphan_cards


def build_static_slides(
    *,
    step: "DraftStructuringStep",
    blueprint: TemplateBlueprint,
    spec_lookup: Mapping[str, Slide],
    cards_by_slot: Mapping[str, PrepareCard],
    layout_lookup: Mapping[str, str],
) -> tuple[list[DraftSection], list[GenerateReadySlide], list[MappingLogSlide]]:
    section = DraftSection(name="Static Template", order=1, status="draft", slides=[])
    sections = [section]
    generate_ready_slides: list[GenerateReadySlide] = []
    mapping_slides: list[MappingLogSlide] = []

    for page_no, blueprint_slide in enumerate(blueprint.slides, start=1):
        spec_slide = spec_lookup.get(blueprint_slide.slide_id)
        layout_id = spec_slide.layout if spec_slide else blueprint_slide.layout
        layout_name = layout_lookup.get(layout_id, layout_id)

        slide_card = DraftSlideCard(
            ref_id=spec_slide.id if spec_slide else blueprint_slide.slide_id,
            order=page_no,
            layout_hint=layout_id,
            locked=False,
            status="draft",
            layout_candidates=[DraftLayoutCandidate(layout_id=layout_id, score=1.0)],
            appendix=False,
        )
        section.slides.append(slide_card)

        elements: dict[str, Any] = {}
        slot_records: list[dict[str, Any]] = []
        slide_note_lines: list[str] = []

        for slot in blueprint_slide.slots:
            card = cards_by_slot.get(slot.slot_id)
            fulfilled = card_slot_fulfilled(card)
            slot_record = {
                "slot_id": slot.slot_id,
                "anchor": slot.anchor,
                "required": slot.required,
                "card_id": card.card_id if card else None,
                "fulfilled": fulfilled,
                "default_applied": False,
            }
            if card is None:
                applied_default = False
                if slot.default_text:
                    elements[slot.anchor] = list(slot.default_text)
                    applied_default = True
                elif slot.default_payload:
                    elements[slot.anchor] = deepcopy(slot.default_payload)
                    applied_default = True
                slot_record["default_applied"] = applied_default
                slot_records.append(slot_record)
                continue
            slot_records.append(slot_record)
            card_notes = card.notes_text()
            if card_notes:
                slide_note_lines.extend(card_notes)
            lines = card_to_lines(card)
            assign_slot_to_elements(elements, slot, card, lines)

        merge_slide_notes(elements, slide_note_lines)

        sources: list[str] = []
        sources.append(spec_slide.id if spec_slide is not None else blueprint_slide.slide_id)

        auto_draw_payload: list[dict[str, Any]] = []
        if spec_slide is not None and spec_slide.auto_draw_boxes:
            auto_draw_payload = [
                {
                    "anchor": anchor,
                    "left_in": box.left_in,
                    "top_in": box.top_in,
                    "width_in": box.width_in,
                    "height_in": box.height_in,
                }
                for anchor, box in spec_slide.auto_draw_boxes.items()
            ]

        slide_meta = MappingSlideMeta(
            section="Static Template",
            page_no=page_no,
            sources=sources,
            fallback="none",
            auto_draw=auto_draw_payload,
            layout_mode="static",
            blueprint_slide_id=blueprint_slide.slide_id,
            blueprint_slots=slot_records,
            prototype_index=blueprint_slide.prototype_index,
        )

        generate_ready_slides.append(
            GenerateReadySlide(
                layout_id=layout_id,
                layout_name=layout_name,
                elements=elements,
                meta=slide_meta,
            )
        )

        mapping_slides.append(
            MappingLogSlide(
                ref_id=slide_card.ref_id,
                selected_layout=layout_id,
                candidates=[MappingCandidate(layout_id=layout_id, score=1.0)],
                fallback=MappingFallbackState(),
                warnings=[],
                layout_description={
                    "layout_id": layout_id,
                    "layout_name": layout_name,
                    "blueprint_slots": slot_records,
                    "auto_draw": auto_draw_payload,
                    "mode": "static",
                },
            )
        )

    return sections, generate_ready_slides, mapping_slides
