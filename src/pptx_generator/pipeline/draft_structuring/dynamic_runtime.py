"""Helpers for the dynamic draft structuring flow."""

from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from ...draft_intel import load_analysis_summary
from ...prepare.models import PrepareDocument, PrepareGenerationMeta
from ...models import (
    ContentApprovalDocument,
    DraftAnalyzerSummary,
    DraftDocument,
    GenerateReadyDocument,
)
from ..base import PipelineContext
from ..slide_alignment import SlideIdAligner, SlideIdAlignerOptions
from ...draft_recommender import CardLayoutRecommender, CardLayoutRecommenderConfig, LayoutProfile
from ...api.draft_store import BoardAlreadyExistsError, DraftStore
from .errors import DraftStructuringError
from .layout_loader import load_layouts
from .generate_ready_runtime import (
    build_generate_ready_document,
    build_generate_ready_meta_payload,
)

if TYPE_CHECKING:  # pragma: no cover - import-time only for typing.
    from .step import DraftStructuringStep


logger = logging.getLogger(__name__)


def get_content_document(
    step: DraftStructuringStep, context: PipelineContext
) -> ContentApprovalDocument | None:
    artifact = context.artifacts.get("content_approved")
    if artifact is None:
        logger.info("content_approved が存在しないため draft_structuring をスキップします")
        return None
    if not isinstance(artifact, ContentApprovalDocument):
        msg = "content_approved artifact の型が不正です"
        raise DraftStructuringError(msg)
    return artifact


def should_use_static_mode(prepare_meta: PrepareGenerationMeta) -> bool:
    return (prepare_meta.mode or "dynamic") == "static"


def get_prepare_meta(step: DraftStructuringStep, context: PipelineContext) -> PrepareGenerationMeta:
    prepare_meta = context.artifacts.get("prepare_generation_meta")
    if not isinstance(prepare_meta, PrepareGenerationMeta):
        msg = "prepare_generation_meta artifact が見つからないか型が不正です"
        raise DraftStructuringError(msg)
    if prepare_meta.mode not in {"dynamic", "static"}:
        msg = "prepare_generation_meta の mode が未設定、または不正な値です"
        raise DraftStructuringError(msg)
    return prepare_meta


def align_content_if_needed(
    step: DraftStructuringStep,
    context: PipelineContext,
    document: ContentApprovalDocument,
) -> ContentApprovalDocument:
    step._alignment_records = None  # type: ignore[attr-defined]
    if not step.options.enable_slide_alignment:
        return document

    aligner = SlideIdAligner(
        SlideIdAlignerOptions(
            confidence_threshold=step.options.slide_alignment_threshold,
            max_candidates=step.options.slide_alignment_max_candidates,
        )
    )
    prepare_document = context.artifacts.get("prepare_document")
    alignment = aligner.align(
        spec=context.spec,
        prepare_document=prepare_document if isinstance(prepare_document, PrepareDocument) else None,
        content_document=document,
    )

    step._alignment_records = alignment.records  # type: ignore[attr-defined]
    context.add_artifact("content_alignment_meta", alignment.meta)
    context.add_artifact(
        "content_alignment_records",
        [asdict(record) for record in alignment.records],
    )

    pending_cards = [record.card_id for record in alignment.records if record.status == "pending"]
    if pending_cards:
        logger.error("Slide alignment 未確定カード: %s", ", ".join(sorted(set(pending_cards))))
        msg = "Slide alignment に失敗したカードがあります: " + ", ".join(sorted(set(pending_cards)))
        raise DraftStructuringError(msg)

    document = alignment.document
    context.add_artifact("content_approved", document)
    return document


def prepare_dynamic_inputs(
    step: DraftStructuringStep,
    *,
    context: PipelineContext,
    prepare_meta: PrepareGenerationMeta,
) -> Tuple[List[LayoutProfile], Dict[str, DraftAnalyzerSummary], CardLayoutRecommender, bool]:
    layouts = load_layouts(
        path=step.options.layouts_path,
        spec_source_path=Path(step.options.spec_source_path) if step.options.spec_source_path else None,
    )
    step._layout_name_lookup = {profile.layout_id: profile.layout_name for profile in layouts}  # type: ignore[attr-defined]
    step._layout_catalog = {profile.layout_id: profile for profile in layouts}  # type: ignore[attr-defined]

    analyzer_map = (
        load_analysis_summary(step.options.analysis_summary_path)
        if step.options.analysis_summary_path
        else {}
    )

    config = CardLayoutRecommenderConfig(
        enable_ai=step.options.enable_ai_recommender,
        ai_weight=step.options.ai_weight,
        diversity_weight=step.options.diversity_weight,
        max_candidates=step.options.max_layout_candidates,
        policy_path=step.options.layout_ai_policy_path,
        policy_id=step.options.layout_ai_policy_id,
        enable_simulated_ai=step.options.enable_ai_simulation,
    )
    recommender = CardLayoutRecommender(config)
    step._recommender = recommender  # type: ignore[attr-defined]

    dynamic_prepare = prepare_meta.mode == "dynamic"
    return layouts, analyzer_map, recommender, dynamic_prepare


def persist_dynamic_outputs(
    step: DraftStructuringStep,
    *,
    context: PipelineContext,
    draft: DraftDocument,
    mapping_logs: List[Dict[str, Any]],
    ai_summary: Dict[str, Any],
    content_document: ContentApprovalDocument,
) -> None:
    output_dir = step.options.output_dir or context.workdir
    output_dir.mkdir(parents=True, exist_ok=True)

    draft_path = output_dir / step.options.draft_filename
    approved_path = output_dir / step.options.approved_filename
    log_path = output_dir / step.options.log_filename
    mapping_log_path = output_dir / step.options.mapping_log_filename

    step._write_document(draft_path, draft)  # type: ignore[attr-defined]
    step._write_document(approved_path, draft)  # type: ignore[attr-defined]
    step._write_log(log_path, [])  # type: ignore[attr-defined]
    step._write_json(mapping_log_path, mapping_logs)  # type: ignore[attr-defined]

    template_path_value = resolve_template_path(step, context)
    generate_ready = build_generate_ready_document(
        step=step,
        spec=context.spec,
        draft=draft,
        content_document=content_document,
        template_path=template_path_value,
    )

    ready_path = output_dir / step.options.generate_ready_filename
    step._write_json(ready_path, generate_ready.model_dump(mode="json"))  # type: ignore[attr-defined]
    context.add_artifact("generate_ready", generate_ready)
    context.add_artifact("generate_ready_path", str(ready_path))

    ready_meta_payload = build_generate_ready_meta_payload(
        draft=draft,
        generate_ready=generate_ready,
        ai_summary=ai_summary,
    )
    ready_meta_path = output_dir / step.options.generate_ready_meta_filename
    step._write_json(ready_meta_path, ready_meta_payload)  # type: ignore[attr-defined]
    context.add_artifact("generate_ready_meta_path", str(ready_meta_path))

    context.add_artifact("draft_document", draft)
    context.add_artifact("draft_document_path", str(approved_path))
    context.add_artifact("draft_review_log_path", str(log_path))
    context.add_artifact("draft_mapping_log_path", str(mapping_log_path))

    spec_id = step._spec_id_from_title(getattr(context.spec.meta, "title", None))  # type: ignore[attr-defined]
    context.add_artifact("draft_spec_id", spec_id)

    store_dir = step.options.draft_store_dir
    store = DraftStore(base_dir=store_dir if store_dir is not None else None)
    try:
        store.create_board(spec_id, draft)
    except BoardAlreadyExistsError:
        store.overwrite_board(spec_id, draft)

    logger.info(
        "Draft ドキュメントを生成しました: sections=%d",
        len(draft.sections),
    )


def resolve_template_path(
    step: DraftStructuringStep, context: PipelineContext
) -> Path | None:
    spec_template_path = getattr(context.spec.meta, "template_path", None)
    if not spec_template_path:
        return None

    candidate = Path(spec_template_path)
    if candidate.is_absolute():
        return candidate

    spec_source_path = step.options.spec_source_path
    if spec_source_path is not None:
        return (spec_source_path.parent / candidate).resolve()
    return candidate.resolve()
