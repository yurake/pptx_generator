"""Prepare AI 静的モードのカード生成フロー。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Sequence

from ...models import TemplateBlueprint, TemplateBlueprintSlide
from ..errors import PrepareAIOrchestrationError
from ..llm_client import (
    PrepareLLMClient,
    PrepareLLMConfigurationError,
    PrepareLLMResult,
)
from ..prompts import build_prepare_prompt_static
from ...prepare.models import PrepareAIRecord, PrepareCard
from ...prepare.policy import PreparePolicy
from ...prepare.source import PrepareSourceChapter, PrepareSourceDocument
from .types import StaticPromptOverride, StaticSlotEntry

logger = logging.getLogger(__name__)


class StaticModeExecutor:
    """Blueprint ベースの静的カード生成処理を担当する。"""

    def __init__(
        self,
        *,
        llm_client: PrepareLLMClient,
        parse_llm_output: Callable[[PrepareLLMResult], dict[str, Any]],
        build_card_from_entry: Callable[..., PrepareCard],
        compose_raw_text: Callable[[PrepareSourceDocument], str],
        build_chapter_body_blocks: Callable[[PrepareSourceChapter], list[Any]],
        build_chapter_notes: Callable[[Sequence], list[Any]],
        normalize_slot_card_id: Callable[[str], str],
        default_prompt_id: str,
    ) -> None:
        self._llm_client = llm_client
        self._parse_llm_output = parse_llm_output
        self._build_card_from_entry = build_card_from_entry
        self._compose_raw_text = compose_raw_text
        self._build_chapter_body_blocks = build_chapter_body_blocks
        self._build_chapter_notes = build_chapter_notes
        self._normalize_slot_card_id = normalize_slot_card_id
        self._default_prompt_id = default_prompt_id

    # ------------------------------------------------------------------ #
    # 公開 API
    # ------------------------------------------------------------------ #
    def build_cards(
        self,
        *,
        source: PrepareSourceDocument,
        policy: PreparePolicy,
        blueprint: TemplateBlueprint,
        page_limit: int | None,
        prompt_overrides: Sequence[StaticPromptOverride],
        slide_sources: dict[str, PrepareSourceDocument] | None,
        slide_input_refs: dict[str, str] | None,
    ) -> tuple[list[PrepareCard], dict[str, int], list[PrepareAIRecord], list[dict[str, Any]]]:
        if page_limit is not None:
            raise PrepareAIOrchestrationError("static モードでは --page-limit オプションを使用できません")

        slot_entries = self._build_static_slot_entries(blueprint)
        chapter_assignments, required_total, optional_total = self._assign_static_chapters(
            slot_entries=slot_entries,
            chapters=list(source.chapters),
        )

        overrides_by_slide_id, overrides_by_index = self._index_static_overrides(prompt_overrides)
        entries_by_slide = self._group_static_entries_by_slide(slot_entries)

        base_context = source.raw_text or self._compose_raw_text(source)
        base_context = base_context.strip() if isinstance(base_context, str) else ""
        slide_sources = slide_sources or {}
        slide_input_refs = slide_input_refs or {}

        cards: list[PrepareCard] = []
        ai_records: list[PrepareAIRecord] = []
        prompt_usage: list[dict[str, Any]] = []
        required_fulfilled = 0
        optional_used = 0
        now = datetime.now(timezone.utc)

        for slide_index, blueprint_slide in enumerate(blueprint.slides, start=1):
            slide_entries = entries_by_slide.get(blueprint_slide.slide_id, [])
            if not slide_entries:
                continue

            slide_source = slide_sources.get(blueprint_slide.slide_id)
            slide_base_context = self._resolve_static_base_context(
                default_context=base_context,
                slide_source=slide_source,
            )
            slot_specs_payload = self._build_static_slot_specs(
                slide=blueprint_slide,
                slide_entries=slide_entries,
                slide_base_context=slide_base_context,
                chapter_assignments=chapter_assignments,
                slide_source=slide_source,
            )

            override = self._select_static_override(
                slide_id=blueprint_slide.slide_id,
                slide_index=slide_index,
                overrides_by_slide_id=overrides_by_slide_id,
                overrides_by_index=overrides_by_index,
            )
            override_instructions = override.instructions.strip() if override else ""

            payload: dict[str, Any] = {
                "raw_context": {
                    "format": "markdown",
                    "content": slide_base_context,
                },
                "blueprint_slide": {
                    "slide_id": blueprint_slide.slide_id,
                    "layout": blueprint_slide.layout,
                    "required": blueprint_slide.required,
                    "intent_tags": blueprint_slide.intent_tags,
                },
                "slot_specs": slot_specs_payload,
            }
            if override and override_instructions:
                payload["user_directives"] = override_instructions

            llm_result, slots_payload, slot_output_lookup, prompt = self._invoke_static_prompt(payload=payload)

            generated_card_ids: list[str] = []
            for entry in slide_entries:
                card, has_content = self._build_static_card_from_slot(
                    slot_entry=entry,
                    blueprint_slide=blueprint_slide,
                    chapter_assignments=chapter_assignments,
                    slot_output_lookup=slot_output_lookup,
                    policy=policy,
                    generated_at=now,
                    slide_source=slide_source,
                )
                cards.append(card)
                generated_card_ids.append(card.card_id)

                if entry.slot.required:
                    if has_content:
                        required_fulfilled += 1
                else:
                    if has_content:
                        optional_used += 1

            if not generated_card_ids:
                continue

            ai_records.append(
                PrepareAIRecord(
                    card_id=blueprint_slide.slide_id,
                    batch_card_ids=generated_card_ids,
                    prompt_template=policy.prompt_template_id or self._default_prompt_id,
                    model=llm_result.model,
                    prompt_fragment=prompt[:200],
                    response_digest=json.dumps(slots_payload, ensure_ascii=False)[:200],
                    warnings=list(llm_result.warnings),
                    slide_input_path=slide_input_refs.get(blueprint_slide.slide_id),
                    prompt_template_path=override.template_path if override else None,
                    prompt_template_instructions=override_instructions if override_instructions else None,
                    tokens=llm_result.tokens,
                )
            )

            if override and override_instructions:
                prompt_usage.append(
                    {
                        "slide_id": blueprint_slide.slide_id,
                        "slide_index": slide_index,
                        "template_path": override.template_path,
                    }
                )

        slot_summary = {
            "required_total": required_total,
            "required_fulfilled": required_fulfilled,
            "optional_total": optional_total,
            "optional_used": optional_used,
        }
        return cards, slot_summary, ai_records, prompt_usage

    # ------------------------------------------------------------------ #
    # 内部ヘルパー
    # ------------------------------------------------------------------ #
    def _build_static_slot_entries(self, blueprint: TemplateBlueprint) -> list[StaticSlotEntry]:
        entries: list[StaticSlotEntry] = []
        for slide_index, slide in enumerate(blueprint.slides, start=1):
            for slot in slide.slots:
                entries.append(
                    StaticSlotEntry(
                        order=len(entries),
                        slide_index=slide_index,
                        slide=slide,
                        slot=slot,
                    )
                )
        return entries

    def _assign_static_chapters(
        self,
        *,
        slot_entries: Sequence[StaticSlotEntry],
        chapters: Sequence[PrepareSourceChapter],
    ) -> tuple[dict[int, PrepareSourceChapter], int, int]:
        required_entries = [entry for entry in slot_entries if entry.slot.required]
        optional_entries = [entry for entry in slot_entries if not entry.slot.required]

        chapter_assignments: dict[int, PrepareSourceChapter] = {}
        chapter_iter_index = 0

        if len(chapters) < len(required_entries):
            logger.warning(
                "Blueprint の必須 slot 数 (%d) に対し、入力章数が不足しています (%d)。不足分は原稿全体から補完します。",
                len(required_entries),
                len(chapters),
            )

        for entry in required_entries:
            if chapter_iter_index >= len(chapters):
                break
            chapter_assignments[entry.order] = chapters[chapter_iter_index]
            chapter_iter_index += 1

        for entry in optional_entries:
            if chapter_iter_index >= len(chapters):
                break
            chapter_assignments[entry.order] = chapters[chapter_iter_index]
            chapter_iter_index += 1

        return chapter_assignments, len(required_entries), len(optional_entries)

    @staticmethod
    def _index_static_overrides(
        prompt_overrides: Sequence[StaticPromptOverride],
    ) -> tuple[dict[str, StaticPromptOverride], dict[int, StaticPromptOverride]]:
        overrides_by_slide_id: dict[str, StaticPromptOverride] = {}
        overrides_by_index: dict[int, StaticPromptOverride] = {}
        for override in prompt_overrides:
            if override.slide_id:
                overrides_by_slide_id[override.slide_id] = override
            overrides_by_index[override.slide_index] = override
        return overrides_by_slide_id, overrides_by_index

    @staticmethod
    def _group_static_entries_by_slide(
        slot_entries: Sequence[StaticSlotEntry],
    ) -> dict[str, list[StaticSlotEntry]]:
        grouped: dict[str, list[StaticSlotEntry]] = {}
        for entry in slot_entries:
            grouped.setdefault(entry.slide.slide_id, []).append(entry)
        return grouped

    def _resolve_static_base_context(
        self,
        *,
        default_context: str,
        slide_source: PrepareSourceDocument | None,
    ) -> str:
        if slide_source is None:
            return default_context

        candidate = slide_source.raw_text or self._compose_raw_text(slide_source)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        return default_context

    def _build_static_slot_specs(
        self,
        *,
        slide: TemplateBlueprintSlide,
        slide_entries: Sequence[StaticSlotEntry],
        slide_base_context: str,
        chapter_assignments: dict[int, PrepareSourceChapter],
        slide_source: PrepareSourceDocument | None,
    ) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for entry in slide_entries:
            chapter = chapter_assignments.get(entry.order)
            if slide_source is not None:
                chapter = None
            context_value = self._build_static_context_value(
                slide=slide,
                slot=entry.slot,
                chapter=chapter,
                slide_base_context=slide_base_context,
            )
            slot_payload = {
                "slot_id": entry.slot.slot_id,
                "anchor": entry.slot.anchor,
                "required": entry.slot.required,
                "intent_tags": entry.slot.intent_tags,
                "content_type": entry.slot.content_type,
            }
            if context_value:
                slot_payload["context"] = context_value
            payload.append(slot_payload)
        return payload

    def _build_static_context_value(
        self,
        *,
        slide: TemplateBlueprintSlide,
        slot,
        chapter: PrepareSourceChapter | None,
        slide_base_context: str,
    ) -> str:
        if chapter is not None:
            context_lines: list[str] = []
            body_blocks = self._build_chapter_body_blocks(chapter)
            notes = self._build_chapter_notes(chapter.supporting_points)
            if chapter.title:
                context_lines.append(chapter.title)
            if chapter.message:
                context_lines.append(chapter.message)
            context_lines.extend(
                block.text.strip()
                for block in body_blocks
                if isinstance(block.text, str) and block.text.strip()
            )
            context_lines.extend(
                note.text.strip()
                for note in notes
                if isinstance(note.text, str) and note.text.strip()
            )
            context_text = "\n".join(context_lines).strip()
            if context_text:
                return context_text

        if slide_base_context:
            return slide_base_context

        labels = [slide.layout or "", slot.anchor or ""]
        return " / ".join(part for part in labels if part).strip()

    @staticmethod
    def _select_static_override(
        *,
        slide_id: str,
        slide_index: int,
        overrides_by_slide_id: dict[str, StaticPromptOverride],
        overrides_by_index: dict[int, StaticPromptOverride],
    ) -> StaticPromptOverride | None:
        override = overrides_by_slide_id.get(slide_id)
        if override is not None:
            return override
        return overrides_by_index.get(slide_index)

    def _invoke_static_prompt(
        self,
        *,
        payload: dict[str, Any],
    ) -> tuple[PrepareLLMResult, list[dict[str, Any]], dict[str, dict[str, Any]], str]:
        prompt = build_prepare_prompt_static(payload)
        try:
            llm_result = self._llm_client.generate(prompt, model_hint=None)
        except PrepareLLMConfigurationError as exc:
            raise PrepareAIOrchestrationError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise PrepareAIOrchestrationError(f"LLM 呼び出しに失敗しました: {exc}") from exc

        data = self._parse_llm_output(llm_result)
        slots_payload = data.get("slots")
        if not isinstance(slots_payload, list):
            raise PrepareAIOrchestrationError("LLM 応答に 'slots' 配列が含まれていません")
        slot_output_lookup = {
            str(item.get("slot_id")): item
            for item in slots_payload
            if isinstance(item, dict) and item.get("slot_id")
        }
        return llm_result, slots_payload, slot_output_lookup, prompt

    def _build_static_card_from_slot(
        self,
        *,
        slot_entry: StaticSlotEntry,
        blueprint_slide: TemplateBlueprintSlide,
        chapter_assignments: dict[int, PrepareSourceChapter],
        slot_output_lookup: dict[str, dict[str, Any]],
        policy: PreparePolicy,
        generated_at: datetime,
        slide_source: PrepareSourceDocument | None,
    ) -> tuple[PrepareCard, bool]:
        chapter = chapter_assignments.get(slot_entry.order)
        if slide_source is not None:
            chapter = None

        slot_output = slot_output_lookup.get(slot_entry.slot.slot_id) or {}
        entry_payload = {
            "card_id": slot_entry.slot.slot_id,
            "story_phase": policy.resolve_story_phase(slot_entry.order),
            "intent_tags": slot_entry.slot.intent_tags or [policy.resolve_story_phase(slot_entry.order)],
            "title": slot_output.get("title"),
            "headline": slot_output.get("headline"),
            "subtitle": slot_output.get("subtitle"),
            "body": slot_output.get("body") or [],
            "notes": slot_output.get("notes") or [],
        }
        entry_payload["card_id"] = self._normalize_slot_card_id(slot_entry.slot.slot_id)

        card = self._build_card_from_entry(
            entry_payload,
            index=slot_entry.order,
            policy=policy,
            generated_at=generated_at,
            is_title_card=False,
            default_title=chapter.title if chapter is not None else blueprint_slide.layout,
        )

        blueprint_meta = {
            "slide_id": blueprint_slide.slide_id,
            "layout": blueprint_slide.layout,
            "slot_id": slot_entry.slot.slot_id,
            "anchor": slot_entry.slot.anchor,
            "content_type": slot_entry.slot.content_type,
            "required": slot_entry.slot.required,
            "fulfilled": False,
            "intent_tags": slot_entry.slot.intent_tags,
        }

        meta: dict[str, Any] = {}
        if isinstance(card.meta, dict):
            meta.update(card.meta)
        meta.update({"mode": "static", "blueprint": blueprint_meta})
        if chapter is not None:
            meta["source_chapter"] = {"id": chapter.id, "title": chapter.title}

        card.card_id = entry_payload["card_id"]
        card.order = slot_entry.order + 1
        card.meta = meta

        has_visible_content = bool(
            card.content.title
            or card.content.headline
            or (card.content.subtitle and card.content.subtitle.strip())
            or card.content.body
        )
        has_content = bool(slot_entry.slot.slot_id in slot_output_lookup and has_visible_content)
        card.meta["blueprint"]["fulfilled"] = has_content  # type: ignore[index]

        return card, has_content
