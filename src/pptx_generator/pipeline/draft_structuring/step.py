"""stage 4 ドラフト構成設計ステップ。"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Iterable, Sequence

from ...prepare.models import PrepareCard, PrepareDocument, PrepareGenerationMeta
from ...models import (
    ContentApprovalDocument,
    ContentSlide,
    DraftAnalyzerSummary,
    DraftDocument,
    DraftMeta,
    DraftSection,
    DraftSlideCard,
    DraftLayoutCandidate,
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
    TemplateBlueprintSlide,
    TemplateBlueprintSlot,
    Slide,
    TemplateSpec,
)
from ...draft_recommender import CardLayoutRecommender, LayoutProfile
from ...api.draft_store import DraftStore, BoardAlreadyExistsError
from ..base import PipelineContext
from .errors import DraftStructuringError
from .dynamic_flow import build_dynamic_document
from .dynamic_runtime import (
    align_content_if_needed,
    get_content_document,
    get_prepare_meta,
    prepare_dynamic_inputs,
    persist_dynamic_outputs,
    should_use_static_mode,
)
from .static_runtime import run_static_mode
from .types import DraftStructuringOptions, StaticArtifacts, card_slot_fulfilled, card_slot_id

logger = logging.getLogger(__name__)


class DraftStructuringStep:
    """content_approved と layouts.jsonl から Draft ドキュメントを生成する。"""

    name = "draft_structuring"

    def __init__(self, options: DraftStructuringOptions | None = None) -> None:
        self.options = options or DraftStructuringOptions()
        self._recommender: CardLayoutRecommender | None = None
        self._alignment_records: list | None = None
        self._layout_name_lookup: dict[str, str] = {}
        self._layout_catalog: dict[str, LayoutProfile] = {}

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def run(self, context: PipelineContext) -> None:
        document = get_content_document(self, context)
        if document is None:
            return

        prepare_meta = get_prepare_meta(self, context)
        if should_use_static_mode(prepare_meta):
            run_static_mode(
                step=self,
                context=context,
                content_document=document,
                prepare_meta=prepare_meta,
            )
            return

        document = align_content_if_needed(self, context, document)

        (
            layouts,
            analyzer_map,
            recommender,
            dynamic_prepare,
        ) = prepare_dynamic_inputs(self, context=context, prepare_meta=prepare_meta)

        draft, mapping_logs, ai_summary = build_dynamic_document(
            options=self.options,
            spec=context.spec,
            document=document,
            layouts=layouts,
            analyzer_map=analyzer_map,
            recommender=recommender,
            dynamic_prepare=dynamic_prepare,
        )

        persist_dynamic_outputs(
            self,
            context=context,
            draft=draft,
            mapping_logs=mapping_logs,
            ai_summary=ai_summary,
            content_document=document,
        )

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #

    def _load_layouts(self, path: Path | None) -> list[LayoutProfile]:
        from .layout_loader import load_layouts

        return load_layouts(
            path=path,
            spec_source_path=Path(self.options.spec_source_path) if self.options.spec_source_path else None,
        )

    @staticmethod
    def _summarize_placeholders(
        placeholders: Sequence[dict[str, Any]],
    ) -> dict[str, Any]:
        from .layout_loader import summarize_placeholders

        return summarize_placeholders(placeholders)

    @staticmethod
    def _write_document(path: Path, document: DraftDocument) -> None:
        payload = document.model_dump(mode="json")
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _write_log(path: Path, entries: Iterable[dict[str, object]]) -> None:
        payload = list(entries)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _spec_id_from_title(title: str | None) -> str:
        if not title:
            return "default"
        normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in title)
        normalized = normalized.strip("-") or "default"
        return normalized[:64]

    def _build_generate_ready_document(
        self,
        *,
        spec: JobSpec,
        draft: DraftDocument,
        content_document: ContentApprovalDocument | None,
        template_path: Path | None = None,
    ) -> GenerateReadyDocument:
        from .generate_ready_runtime import build_generate_ready_document

        return build_generate_ready_document(
            step=self,
            spec=spec,
            draft=draft,
            content_document=content_document,
            template_path=template_path,
        )

    def _build_generate_ready_meta_payload(
        self,
        *,
        draft: DraftDocument,
        generate_ready: GenerateReadyDocument,
        ai_summary: dict[str, Any],
    ) -> dict[str, Any]:
        from .generate_ready_runtime import build_generate_ready_meta_payload

        return build_generate_ready_meta_payload(
            draft=draft,
            generate_ready=generate_ready,
            ai_summary=ai_summary,
        )

    @staticmethod
    def _summarize_sections(
        draft: DraftDocument,
    ) -> tuple[list[dict[str, Any]], int, int]:
        from .generate_ready_runtime import summarize_sections

        return summarize_sections(draft)

    @staticmethod
    def _build_template_info(draft: DraftDocument) -> dict[str, Any]:
        from .generate_ready_runtime import build_template_info

        return build_template_info(draft)

    @staticmethod
    def _build_ai_recommendation_block(ai_summary: dict[str, Any]) -> dict[str, Any]:
        from .generate_ready_runtime import build_ai_recommendation_block

        return build_ai_recommendation_block(ai_summary)

    def _build_statistics_block(
        self,
        *,
        generate_ready: GenerateReadyDocument,
        main_slides: int,
        appendix_slides: int,
        ai_summary: dict[str, Any],
    ) -> dict[str, Any]:
        from .generate_ready_runtime import build_statistics_block

        return build_statistics_block(
            generate_ready=generate_ready,
            main_slides=main_slides,
            appendix_slides=appendix_slides,
            ai_summary=ai_summary,
        )

    @staticmethod
    def _apply_optional_generate_ready_meta(
        *,
        payload: dict[str, Any],
        generate_ready: GenerateReadyDocument,
    ) -> None:
        from .generate_ready_runtime import apply_optional_generate_ready_meta

        apply_optional_generate_ready_meta(payload=payload, generate_ready=generate_ready)

    def _merge_slide_elements(
        self,
        spec_slide: Slide | None,
        content_slide: ContentSlide | None,
        layout_profile: LayoutProfile | None,
    ) -> dict[str, Any]:
        from .slide_elements import merge_slide_elements

        return merge_slide_elements(
            content_slide=content_slide,
            spec_slide=spec_slide,
            layout_profile=layout_profile,
        )

    def _collect_content_elements(
        self,
        content_elements: ContentElements,
        base: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        from .slide_elements import collect_content_elements

        return collect_content_elements(content_elements, base)

    def _merge_spec_slide_details(
        self,
        *,
        elements: dict[str, Any],
        base: dict[str, Any],
        spec_slide: Slide,
        table_payload: dict[str, Any] | None,
    ) -> None:
        from .slide_elements import merge_spec_slide_details

        merge_spec_slide_details(
            elements=elements,
            base=base,
            spec_slide=spec_slide,
            table_payload=table_payload,
        )

    def _apply_table_payload(
        self,
        *,
        elements: dict[str, Any],
        base: dict[str, Any],
        table_payload: dict[str, Any],
        spec_slide: Slide | None,
        layout_profile: LayoutProfile | None,
        content_slide: ContentSlide,
    ) -> None:
        from .slide_elements import apply_table_payload

        apply_table_payload(
            elements=elements,
            base=base,
            table_payload=table_payload,
            spec_slide=spec_slide,
            layout_profile=layout_profile,
            content_slide=content_slide,
        )

    @staticmethod
    def _convert_slide_elements(slide: Slide | None) -> dict[str, Any]:
        from .slide_elements import convert_slide_elements

        return convert_slide_elements(slide)

    @staticmethod
    def _card_to_lines(card: PrepareCard) -> list[str]:
        from .slide_elements import card_to_lines

        return card_to_lines(card)

    @staticmethod
    def _assign_slot_to_elements(
        elements: dict[str, Any],
        slot: TemplateBlueprintSlot,
        card: PrepareCard,
        lines: list[str],
    ) -> None:
        from .slide_elements import assign_slot_to_elements

        assign_slot_to_elements(elements, slot, card, lines)

    @staticmethod
    def _assign_special_anchor(
        elements: dict[str, Any],
        anchor_lower: str,
        card: PrepareCard,
    ) -> bool:
        from .slide_elements import assign_special_anchor

        return assign_special_anchor(elements, anchor_lower, card)

    @staticmethod
    def _assign_table_content(
        elements: dict[str, Any],
        anchor: str,
        card: PrepareCard,
        lines: list[str],
    ) -> None:
        from .slide_elements import assign_table_content

        assign_table_content(elements, anchor, card, lines)

    @staticmethod
    def _assign_text_content(
        elements: dict[str, Any],
        anchor: str,
        anchor_lower: str,
        card: PrepareCard,
        lines: list[str],
    ) -> None:
        from .slide_elements import assign_text_content

        assign_text_content(elements, anchor, anchor_lower, card, lines)

    @staticmethod
    def _extract_text_blocks(card: PrepareCard) -> tuple[list[dict[str, Any]], list[str]]:
        from .slide_elements import extract_text_blocks

        return extract_text_blocks(card)

    @staticmethod
    def _append_bullet_entries(
        raw_items: Any,
        bullet_entries: list[dict[str, Any]],
    ) -> None:
        from .slide_elements import append_bullet_entries

        append_bullet_entries(raw_items, bullet_entries)

    @staticmethod
    def _append_dict_bullet(
        entry: dict[str, Any],
        bullet_entries: list[dict[str, Any]],
    ) -> None:
        from .slide_elements import append_dict_bullet

        append_dict_bullet(entry, bullet_entries)

    @staticmethod
    def _merge_slide_notes(elements: dict[str, Any], note_lines: list[str]) -> None:
        from .slide_elements import merge_slide_notes

        merge_slide_notes(elements, note_lines)

    def _load_template_spec(self, path: Path) -> TemplateSpec:
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            msg = f"template_spec を読み込めません: {path}"
            raise DraftStructuringError(msg) from exc

        try:
            if path.suffix.lower() in {".yaml", ".yml"}:
                import yaml

                payload = yaml.safe_load(text)
                return TemplateSpec.model_validate(payload)
            return TemplateSpec.model_validate_json(text)
        except ValueError as exc:
            msg = f"template_spec の解析に失敗しました: {path}"
            raise DraftStructuringError(msg) from exc

    @staticmethod
    def _compute_blueprint_hash(blueprint: TemplateBlueprint) -> str:
        payload = blueprint.model_dump(mode="json")
        digest = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return f"sha256:{hashlib.sha256(digest.encode('utf-8')).hexdigest()}"

    @staticmethod
    def _compute_content_hash(document: ContentApprovalDocument | None) -> str | None:
        if document is None:
            return None
        try:
            payload = document.model_dump(mode="json")
            digest = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            return hashlib.sha256(digest.encode("utf-8")).hexdigest()
        except (TypeError, ValueError):
            return None
