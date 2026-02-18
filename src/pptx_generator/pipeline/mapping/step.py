"""MappingStep 本体。"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from ..base import PipelineContext, PipelineStage
from ...models import (
    ContentApprovalDocument,
    DraftDocument,
    GenerateReadyDocument,
    GenerateReadyMeta,
    MappingLog,
    MappingLogMeta,
    PipelineFallbackError,
    TemplateStyle,
)
from ...stages.prepare.data_models import PrepareDocument, PrepareCard
from .catalog import load_layout_catalog
from .llm_fit import (
    MappingTextFitClientConfigurationError,
    create_mapping_text_fit_client,
)
from .outputs import (
    finalize_outputs,
    format_template_path,
    resolve_content_hash,
    resolve_template_version,
)
from .processor import MappingSlideProcessor
from .types import MappingAccumulator, MappingOptions
from .work_items import (
    build_card_lookup,
    build_section_lookup,
    build_work_items,
)

logger = logging.getLogger(__name__)


class MappingStep:
    """承認済みドラフトを基に generate_ready.json を生成するステップ。"""

    name = "mapping"
    stage = PipelineStage.MAPPING

    def __init__(self, options: MappingOptions | None = None) -> None:
        self.options = options or MappingOptions()

    def run(self, context: PipelineContext) -> None:
        start = time.perf_counter()
        draft_document = self._require_draft_document(context)
        content_document = self._optional_content_document(context)
        layout_catalog = load_layout_catalog(self.options.layouts_path)
        missing_layouts = {
            slide.layout
            for slide in context.spec.slides
            if slide.layout and slide.layout not in layout_catalog
        }
        if missing_layouts:
            msg = (
                "layouts.jsonl に一致するレイアウトが見つかりませんでした: "
                + ", ".join(sorted(missing_layouts))
            )
            if self.options.strict_layouts:
                logger.error(msg)
                raise PipelineFallbackError(msg)
            logger.warning(msg)

        section_lookup = build_section_lookup(draft_document)
        card_lookup = build_card_lookup(draft_document)
        content_lookup = (
            {slide.id: slide for slide in content_document.slides}
            if content_document is not None
            else {}
        )
        prepare_lookup: dict[str, PrepareCard] | None = None
        prepare_document = context.artifacts.get("prepare_document")
        if isinstance(prepare_document, PrepareDocument):
            prepare_lookup = {card.card_id: card for card in prepare_document.cards}
        spec_lookup = {slide.id: slide for slide in context.spec.slides}

        work_items = build_work_items(
            draft_document=draft_document,
            section_lookup=section_lookup,
            card_lookup=card_lookup,
            content_lookup=content_lookup,
            spec_lookup=spec_lookup,
            spec_slides=context.spec.slides,
        )

        accumulator = MappingAccumulator()
        text_fit_client = None
        text_fit_error: str | None = None
        try:
            text_fit_client = create_mapping_text_fit_client()
        except MappingTextFitClientConfigurationError as exc:
            text_fit_error = str(exc)
            logger.warning("mapping text fit client unavailable: %s", exc)
        processor = MappingSlideProcessor(
            options=self.options,
            layout_catalog=layout_catalog,
            prepare_lookup=prepare_lookup,
            text_fit_client=text_fit_client,
            text_fit_error=text_fit_error,
        )

        previous_layout: str | None = None
        for item in work_items:
            previous_layout = processor.process(
                item=item,
                accumulator=accumulator,
                previous_layout=previous_layout,
            )

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        output_dir = self.options.output_dir or context.workdir
        output_dir.mkdir(parents=True, exist_ok=True)

        template_path_str = self._resolve_template_path(output_dir)

        generate_ready_meta = GenerateReadyMeta(
            template_version=resolve_template_version(
                context=context,
                options=self.options,
            ),
            template_path=template_path_str,
            content_hash=resolve_content_hash(context),
            generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            job_meta=context.spec.meta,
            job_auth=context.spec.auth,
        )

        style_data = context.artifacts.get("template_style_data")
        if isinstance(style_data, TemplateStyle):
            generate_ready_meta.template_style = style_data

        generate_ready_document = GenerateReadyDocument(
            slides=accumulator.generate_ready_slides,
            meta=generate_ready_meta,
        )
        mapping_log = MappingLog(
            slides=accumulator.log_slides,
            meta=MappingLogMeta(
                mapping_time_ms=elapsed_ms,
                fallback_count=len(accumulator.fallback_slide_ids),
                ai_patch_count=accumulator.ai_patch_count,
            ),
        )

        finalize_outputs(
            context=context,
            options=self.options,
            output_dir=output_dir,
            generate_ready_document=generate_ready_document,
            mapping_log=mapping_log,
            accumulator=accumulator,
            template_path_str=template_path_str,
            generate_ready_meta=generate_ready_meta,
            elapsed_ms=elapsed_ms,
        )

        logger.info(
            "generate_ready.json を生成しました: slides=%d fallback=%d ai_patch=%d",
            len(accumulator.generate_ready_slides),
            len(accumulator.fallback_slide_ids),
            accumulator.ai_patch_count,
        )

    # ------------------------------------------------------------------ #
    # private helpers
    # ------------------------------------------------------------------ #
    def _require_draft_document(self, context: PipelineContext) -> DraftDocument:
        draft_document = context.artifacts.get("draft_document")
        if draft_document is None:
            msg = "draft_document が存在しません。stage 3/4 の出力を確認してください。"
            logger.error(msg)
            raise PipelineFallbackError(msg)
        if not isinstance(draft_document, DraftDocument):
            msg = "draft_document artifact の型が不正です。"
            logger.error(msg)
            raise PipelineFallbackError(msg)
        return draft_document

    @staticmethod
    def _optional_content_document(
        context: PipelineContext,
    ) -> ContentApprovalDocument | None:
        document = context.artifacts.get("content_approved")
        if document is None:
            return None
        if not isinstance(document, ContentApprovalDocument):
            msg = "content_approved artifact の型が不正です。"
            logger.error(msg)
            raise PipelineFallbackError(msg)
        return document

    def _resolve_template_path(self, output_dir: Path) -> str | None:
        if self.options.template_path is None:
            return None
        template_candidate = self.options.template_path
        try:
            resolved = template_candidate.resolve()
        except OSError:
            resolved = template_candidate
        return format_template_path(resolved, output_dir)
