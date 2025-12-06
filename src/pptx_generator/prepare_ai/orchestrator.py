from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Literal, Sequence

from ..models import TemplateBlueprint, TemplateBlueprintSlide, TemplateBlueprintSlot
from .errors import PrepareAIOrchestrationError
from .client import PrepareLLMClient, PrepareLLMConfigurationError, PrepareLLMResult, create_prepare_llm_client
from ..prepare.models import (
    PrepareAIRecord,
    PrepareBodyBlock,
    PrepareCard,
    PrepareCardContent,
    PrepareCardRole,
    PrepareDocument,
    PrepareGenerationMeta,
    PrepareNoteEntry,
    PrepareStoryContext,
)
from .prompts import build_prepare_prompt_dynamic
from ..prepare.source import PrepareSourceChapter, PrepareSourceDocument, PrepareSourceSupportingPoint
from .static_mode import StaticModeExecutor, StaticPromptOverride, StaticSlotEntry

logger = logging.getLogger(__name__)

DEFAULT_PROMPT_ID = "prepare.default"


class PrepareAIOrchestrator:
    """PrepareCard 生成オーケストレーター。"""

    def __init__(
        self,
        *,
        llm_client: PrepareLLMClient | None = None,
        default_prompt_id: str = DEFAULT_PROMPT_ID,
    ) -> None:
        self._llm_client = llm_client or create_prepare_llm_client()
        self._default_prompt_id = default_prompt_id

    def generate_document(
        self,
        source: PrepareSourceDocument,
        *,
        page_limit: int | None = None,
        mode: Literal["dynamic", "static"] = "dynamic",
        blueprint: TemplateBlueprint | None = None,
        blueprint_ref: dict[str, str] | None = None,
        prompt_overrides: Sequence[StaticPromptOverride] | None = None,
        slide_sources: dict[str, PrepareSourceDocument] | None = None,
        slide_input_refs: dict[str, str] | None = None,
    ) -> tuple[PrepareDocument, PrepareGenerationMeta, list[PrepareAIRecord]]:
        normalized_mode = (mode or "dynamic").lower()
        if normalized_mode not in {"dynamic", "static"}:
            normalized_mode = "dynamic"

        include_title_page = normalized_mode == "dynamic" and page_limit is None
        prompt_usage: list[dict[str, Any]] | None = None
        slot_summary: dict[str, int] | None = None

        if normalized_mode == "static":
            if blueprint is None:
                raise PrepareAIOrchestrationError("static モードには Blueprint が必要です")
            cards, slot_summary, ai_records, prompt_usage = self._build_cards_static(
                source=source,
                blueprint=blueprint,
                prompt_overrides=prompt_overrides or (),
                slide_sources=slide_sources,
                slide_input_refs=slide_input_refs,
            )
        else:
            cards, ai_records = self._build_cards_dynamic(
                source=source,
                page_limit=page_limit,
                include_title_page=include_title_page,
            )

        story_context = self._build_story_context(cards=cards, source=source)
        prepare_id = source.meta.prepare_id or f"prepare-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        document = PrepareDocument(prepare_id=prepare_id, cards=cards, story_context=story_context)

        constraints: dict[str, Any] | None = None
        if normalized_mode == "dynamic":
            constraints = {}
            if page_limit is not None:
                constraints["max_chapters"] = page_limit
            constraints["include_title_page"] = include_title_page
            if not constraints:
                constraints = None

        meta = PrepareGenerationMeta.from_document(
            document=document,
            policy_id=None,
            source_payload=source.model_dump(mode="json"),
            cards_meta=[self._build_card_meta(card) for card in cards],
            mode=normalized_mode,  # type: ignore[arg-type]
            blueprint_path=blueprint_ref.get("path") if blueprint_ref else None,
            blueprint_hash=blueprint_ref.get("hash") if blueprint_ref else None,
            slot_summary=slot_summary,
            constraints=constraints,
            prompt_templates=prompt_usage,
            slide_inputs=[
                {"slide_id": key, "input_path": value}
                for key, value in (slide_input_refs or {}).items()
            ],
        )
        return document, meta, ai_records

    def _build_cards_dynamic(
        self,
        *,
        source: PrepareSourceDocument,
        page_limit: int | None,
        include_title_page: bool,
    ) -> tuple[list[PrepareCard], list[PrepareAIRecord]]:
        payload = self._build_dynamic_prompt_payload(
            source,
            page_limit=page_limit,
            include_title_page=include_title_page,
        )
        prompt = build_prepare_prompt_dynamic(payload)
        try:
            llm_result = self._llm_client.generate(prompt, model_hint=None)
        except PrepareLLMConfigurationError as exc:
            raise PrepareAIOrchestrationError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise PrepareAIOrchestrationError(f"LLM 呼び出しに失敗しました: {exc}") from exc

        data = self._parse_llm_output(llm_result)
        chapters_payload = data.get("chapters")
        if not isinstance(chapters_payload, list) or not chapters_payload:
            raise PrepareAIOrchestrationError("LLM 応答に 'chapters' 配列が含まれていません")

        if page_limit is not None:
            chapters_payload = chapters_payload[:page_limit]

        now = datetime.now(timezone.utc)
        cards: list[PrepareCard] = []
        ai_records: list[PrepareAIRecord] = []

        for index, entry in enumerate(chapters_payload):
            is_title_card = include_title_page and index == 0
            card = self._build_card_from_llm_entry(
                entry,
                index=index,
                generated_at=now,
                is_title_card=is_title_card,
                default_title=source.meta.title,
            )
            cards.append(card)

            ai_records.append(
                PrepareAIRecord(
                    card_id=card.card_id,
                    prompt_template=self._default_prompt_id,
                    model=llm_result.model,
                    prompt_fragment=prompt[:200],
                    response_digest=json.dumps(entry, ensure_ascii=False)[:200],
                    warnings=llm_result.warnings + entry.get("warnings", []),
                    tokens=llm_result.tokens if index == 0 else {},
                )
            )

        if include_title_page and not any(card.content.title for card in cards):
            title_card = self._build_default_title_card(source=source, generated_at=now)
            cards.insert(0, title_card)
            ai_records.insert(
                0,
                PrepareAIRecord(
                    card_id=title_card.card_id,
                    prompt_template=self._default_prompt_id,
                    model="manual",
                    prompt_fragment=None,
                    response_digest="auto title page",
                    warnings=["inserted_title_page"],
                    tokens={},
                ),
            )

        for order, card in enumerate(cards, start=1):
            card.order = order

        return cards, ai_records

    def _build_dynamic_prompt_payload(
        self,
        source: PrepareSourceDocument,
        *,
        page_limit: int | None,
        include_title_page: bool,
    ) -> dict[str, Any]:
        raw_text = source.raw_text
        if not raw_text:
            raw_text = self._compose_raw_text(source)

        existing_outline = [chapter.model_dump(mode="json") for chapter in source.chapters]
        constraints: dict[str, Any] = {}
        if page_limit is not None:
            constraints["max_chapters"] = page_limit

        payload: dict[str, Any] = {
            "raw_context": {
                "format": "markdown",
                "content": raw_text,
            }
        }

        if existing_outline:
            payload.setdefault("hints", {})["existing_outline"] = existing_outline
        if constraints:
            payload["constraints"] = constraints
        payload.setdefault("options", {})["include_title_page"] = include_title_page

        return payload

    def _compose_raw_text(self, source: PrepareSourceDocument) -> str:
        lines: list[str] = []
        if source.meta.objective:
            lines.append(source.meta.objective)
        for chapter in source.chapters:
            if chapter.title:
                lines.append(f"## {chapter.title}")
            if chapter.message:
                lines.append(chapter.message)
            for detail in chapter.details:
                if detail:
                    lines.append(detail)
            for item in chapter.supporting_points:
                statement = getattr(item, "statement", None)
                if statement:
                    lines.append(f"- {statement}")
        return "\n".join(lines).strip()

    def _parse_llm_output(self, result: PrepareLLMResult) -> dict[str, Any]:
        text = result.text.strip()
        if not text:
            raise PrepareAIOrchestrationError("LLM 応答が空でした")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning("LLM 応答の JSON 解析に失敗: %s", exc)
            raise PrepareAIOrchestrationError("LLM 応答を JSON として解析できませんでした") from exc

    def _build_card_from_llm_entry(
        self,
        entry: dict[str, Any],
        *,
        index: int,
        generated_at: datetime,
        is_title_card: bool,
        default_title: str | None,
    ) -> PrepareCard:
        heading_source = str(entry.get("title") or entry.get("headline") or entry.get("message") or f"Chapter {index + 1}")
        if is_title_card:
            title = str(entry.get("title") or default_title or heading_source)
            headline = None
        else:
            headline = str(entry.get("headline") or entry.get("title") or heading_source)
            title = None

        card_id = str(
            entry.get("card_id")
            or ("title" if is_title_card else self._slugify(headline or heading_source))
            or f"chapter-{index + 1}"
        )

        raw_phase = entry.get("story_phase")
        story_phase = str(raw_phase).strip().lower() if isinstance(raw_phase, str) and raw_phase.strip() else None

        intent_tags_raw = entry.get("intent_tags")
        if isinstance(intent_tags_raw, list):
            intent_tags = [str(tag).strip() for tag in intent_tags_raw if str(tag).strip()]
        else:
            intent_tags = []
        if not intent_tags and story_phase:
            intent_tags = [story_phase]

        subtitle_raw = entry.get("subtitle") or entry.get("chapter") or entry.get("section")
        subtitle = str(subtitle_raw).strip() if isinstance(subtitle_raw, str) and subtitle_raw.strip() else None

        body_blocks = self._build_body_blocks(entry.get("body") or entry.get("narrative"))
        notes = self._build_note_entries(entry)

        role = PrepareCardRole(story_phase=story_phase, intent_tags=intent_tags)
        content = PrepareCardContent(title=title, headline=headline, subtitle=subtitle, body=body_blocks, notes=notes)

        return PrepareCard(
            card_id=card_id,
            order=index + 1,
            role=role,
            content=content,
            meta={"generated_at": generated_at.isoformat()},
        )

    def _build_body_blocks(self, payload: Any) -> list[PrepareBodyBlock]:
        blocks: list[PrepareBodyBlock]

        if isinstance(payload, list):
            blocks = []
            for item in payload:
                blocks.extend(self._build_blocks_from_collection_item(item))
        elif isinstance(payload, dict):
            block = self._build_block_from_mapping(payload)
            blocks = [block] if block else []
        elif isinstance(payload, str):
            text = payload.strip()
            blocks = [PrepareBodyBlock(type="paragraph", text=text)] if text else []
        else:
            blocks = []

        return blocks or [self._make_placeholder_block()]

    def _build_blocks_from_collection_item(self, item: Any) -> list[PrepareBodyBlock]:
        if isinstance(item, dict):
            block = self._build_block_from_mapping(item)
            return [block] if block else []
        if isinstance(item, str):
            text = item.strip()
            if text:
                return [PrepareBodyBlock(type="paragraph", text=text)]
        return []

    def _build_block_from_mapping(self, payload: dict[str, Any]) -> PrepareBodyBlock | None:
        block_type = str(payload.get("type") or "paragraph").strip() or "paragraph"
        text = payload.get("text")
        headers = payload.get("headers")
        rows = payload.get("rows")
        ref = payload.get("ref")
        description = payload.get("description")
        data = payload.get("data")
        items = payload.get("items")

        normalized_items = self._normalize_bullet_items(items, text)
        if normalized_items:
            text = None

        if not self._has_block_content(text, headers, rows, description, data, normalized_items):
            return None

        data_dict: dict[str, Any] | None = data if isinstance(data, dict) else None
        if normalized_items:
            if data_dict is None:
                data_dict = {}
            data_dict["items"] = normalized_items

        return PrepareBodyBlock(
            type=block_type,
            text=text,
            headers=headers,
            rows=rows,
            ref=ref,
            description=description,
            data=data_dict,
        )

    @staticmethod
    def _make_placeholder_block() -> PrepareBodyBlock:
        return PrepareBodyBlock(type="placeholder", text="内容を確認中")

    @staticmethod
    def _normalize_bullet_items(raw_items: Any, fallback_text: Any) -> list[dict[str, Any]]:
        normalized = PrepareAIOrchestrator._normalize_bullet_list(raw_items)
        if normalized:
            return normalized
        return PrepareAIOrchestrator._normalize_bullet_fallback(fallback_text)

    @staticmethod
    def _normalize_bullet_list(raw_items: Any) -> list[dict[str, Any]]:
        if not isinstance(raw_items, list):
            return []
        result: list[dict[str, Any]] = []
        for entry in raw_items:
            bullet = PrepareAIOrchestrator._normalize_single_bullet_entry(entry)
            if bullet:
                result.append(bullet)
        return result

    @staticmethod
    def _normalize_bullet_fallback(fallback_text: Any) -> list[dict[str, Any]]:
        fallback = str(fallback_text).strip() if isinstance(fallback_text, str) else None
        if not fallback:
            return []
        normalized: list[dict[str, Any]] = []
        for line in fallback.splitlines():
            stripped = line.strip()
            if stripped.startswith("-"):
                stripped = stripped.lstrip("-").strip()
            if stripped:
                normalized.append({"text": stripped, "level": 0})
        return normalized

    @staticmethod
    def _normalize_single_bullet_entry(entry: Any) -> dict[str, Any] | None:
        if isinstance(entry, str):
            line = entry.strip()
            return {"text": line, "level": 0} if line else None
        if isinstance(entry, dict):
            line = str(entry.get("text") or "").strip()
            if not line:
                return None
            level_raw = entry.get("level", 0)
            try:
                level = max(int(level_raw), 0)
            except (TypeError, ValueError):
                level = 0
            bullet_entry: dict[str, Any] = {"text": line, "level": level}
            for key, value in entry.items():
                if key in {"text", "level"}:
                    continue
                bullet_entry[key] = value
            return bullet_entry
        return None

    @staticmethod
    def _has_block_content(
        text: Any,
        headers: Any,
        rows: Any,
        description: Any,
        data: Any,
        normalized_items: list[dict[str, Any]],
    ) -> bool:
        return any(
            [
                isinstance(text, str) and text.strip(),
                isinstance(headers, list) and any(str(h).strip() for h in headers),
                isinstance(rows, list) and any(row for row in rows),
                isinstance(description, str) and description.strip(),
                isinstance(data, dict) and data,
                bool(normalized_items),
            ]
        )

    def _build_note_entries(self, entry: dict[str, Any]) -> list[PrepareNoteEntry]:
        notes: list[PrepareNoteEntry] = []
        notes_payload = entry.get("notes")
        if isinstance(notes_payload, list):
            for item in notes_payload:
                if isinstance(item, dict):
                    text = str(item.get("text") or "").strip()
                    if not text:
                        continue
                    note_type = str(item.get("type") or "note").strip() or "note"
                    notes.append(PrepareNoteEntry(type=note_type, text=text))
                elif isinstance(item, str) and item.strip():
                    notes.append(PrepareNoteEntry(text=item.strip()))
        elif isinstance(notes_payload, str) and notes_payload.strip():
            notes.append(PrepareNoteEntry(text=notes_payload.strip()))

        # 旧スキーマ互換: supporting_points をノートへ変換
        if not notes:
            supporting = entry.get("supporting_points")
            if isinstance(supporting, list):
                for item in supporting:
                    if isinstance(item, dict):
                        statement = str(item.get("statement") or "").strip()
                    else:
                        statement = str(item or "").strip()
                    if statement:
                        notes.append(PrepareNoteEntry(type="rationale", text=statement))

        return notes

    def _build_default_title_card(
        self,
        *,
        source: PrepareSourceDocument,
        generated_at: datetime,
    ) -> PrepareCard:
        title_text = (source.meta.title or source.meta.prepare_id or "Proposal").strip()
        subtitle = source.meta.client
        body_blocks: list[PrepareBodyBlock] = []
        if source.meta.objective:
            body_blocks.append(PrepareBodyBlock(type="paragraph", text=source.meta.objective))

        role = PrepareCardRole(story_phase=None, intent_tags=[])
        content = PrepareCardContent(title=title_text, subtitle=subtitle, body=body_blocks, notes=[])
        return PrepareCard(
            card_id="title-page",
            order=1,
            role=role,
            content=content,
            meta={"generated_at": generated_at.isoformat(), "auto_title": True},
        )

    def _build_chapter_body_blocks(self, chapter: PrepareSourceChapter) -> list[PrepareBodyBlock]:
        blocks: list[PrepareBodyBlock] = []
        for detail in chapter.details:
            text = (detail or "").strip()
            if not text:
                continue
            blocks.append(PrepareBodyBlock(type="paragraph", text=text))
        if not blocks and chapter.message:
            blocks.append(PrepareBodyBlock(type="paragraph", text=chapter.message))
        if not blocks:
            blocks.append(PrepareBodyBlock(type="placeholder", text="内容を確認中"))
        return blocks

    def _build_chapter_notes(self, supporting_points: list[PrepareSourceSupportingPoint]) -> list[PrepareNoteEntry]:
        notes: list[PrepareNoteEntry] = []
        for supporting in supporting_points:
            statement = (supporting.statement or "").strip()
            if not statement:
                continue
            evidence = ""
            if supporting.evidence_type and supporting.evidence_value:
                evidence = f" ({supporting.evidence_type}: {supporting.evidence_value})"
            notes.append(PrepareNoteEntry(type="rationale", text=f"{statement}{evidence}"))
        return notes


    def _build_cards_static(
        self,
        *,
        source: PrepareSourceDocument,
        blueprint: TemplateBlueprint,
        prompt_overrides: Sequence[StaticPromptOverride],
        slide_sources: dict[str, PrepareSourceDocument] | None,
        slide_input_refs: dict[str, str] | None,
    ) -> tuple[list[PrepareCard], dict[str, int], list[PrepareAIRecord], list[dict[str, Any]]]:
        executor = StaticModeExecutor(
            llm_client=self._llm_client,
            parse_llm_output=self._parse_llm_output,
            build_card_from_entry=self._build_card_from_llm_entry,
            compose_raw_text=self._compose_raw_text,
            build_chapter_body_blocks=self._build_chapter_body_blocks,
            build_chapter_notes=self._build_chapter_notes,
            normalize_slot_card_id=self._normalize_slot_card_id,
            default_prompt_id=self._default_prompt_id,
        )
        return executor.build_cards(
            source=source,
            blueprint=blueprint,
            prompt_overrides=prompt_overrides,
            slide_sources=slide_sources,
            slide_input_refs=slide_input_refs,
            resolve_slot_role=self._resolve_static_role,
        )

    @staticmethod
    def _resolve_static_role(
        slot_entry: StaticSlotEntry,
        blueprint_slide: TemplateBlueprintSlide,
        chapter: PrepareSourceChapter | None,
    ) -> tuple[str | None, list[str]]:
        story_phase: str | None = None
        if chapter and chapter.story_hint:
            hint = str(chapter.story_hint).strip()
            if hint:
                story_phase = hint

        intent_candidates: list[str] = []
        sources = (
            chapter.intent_tags if chapter else None,
            slot_entry.slot.intent_tags,
            blueprint_slide.intent_tags,
        )
        for values in sources:
            if not values:
                continue
            for value in values:
                text = str(value).strip()
                if text:
                    intent_candidates.append(text)

        if story_phase is None and intent_candidates:
            story_phase = intent_candidates[0]

        return story_phase, intent_candidates

    @staticmethod
    def _normalize_slot_card_id(slot_id: str) -> str:
        normalized = slot_id.lower().replace("/", "-").replace(".", "-")
        normalized = normalized.replace(" ", "-")
        filtered = [ch for ch in normalized if ch.isalnum() or ch in {"-"}]
        result = "".join(filtered)
        return result or "slot"

    def _build_story_context(
        self,
        *,
        cards: Sequence[PrepareCard],
        source: PrepareSourceDocument,
    ) -> PrepareStoryContext:
        chapters: list[dict[str, Any]] = []

        if cards:
            seen: set[str] = set()
            for card in cards:
                if card.card_id in seen:
                    continue
                seen.add(card.card_id)
                chapters.append(
                    {
                        "id": card.card_id,
                        "title": card.headline_or_title(),
                        "description": card.content.subtitle or card.content.headline,
                    }
                )
        elif source.chapters:
            for chapter in source.chapters:
                chapters.append(
                    {
                        "id": chapter.id,
                        "title": chapter.title,
                        "description": chapter.message,
                    }
                )

        tone = getattr(source.meta, "objective", None)

        return PrepareStoryContext.model_validate(
            {
                "chapters": chapters,
                "tone": tone,
                "must_have_messages": [],
            }
        )

    def _build_card_meta(self, card: PrepareCard) -> dict[str, Any]:
        payload = {
            "card_id": card.card_id,
            "intent_tags": card.role.intent_tags,
            "story_phase": card.role.story_phase,
            "content_hash": self._hash_card(card),
            "body_blocks": len(card.content.body),
            "note_entries": len(card.content.notes),
        }
        blueprint_meta = card.meta.get("blueprint") if isinstance(card.meta, dict) else None
        if isinstance(blueprint_meta, dict):
            payload.update(
                {
                    "slide_id": blueprint_meta.get("slide_id"),
                    "slot_id": blueprint_meta.get("slot_id"),
                    "required": blueprint_meta.get("required"),
                    "slot_fulfilled": blueprint_meta.get("fulfilled"),
                }
            )
        return payload

    @staticmethod
    def _hash_card(card: PrepareCard) -> str:
        payload = card.model_dump(mode="json", exclude_none=True)
        digest = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(digest.encode("utf-8")).hexdigest()

    @staticmethod
    def _slugify(value: str) -> str:
        normalized = value.lower()
        normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
        normalized = normalized.strip("-")
        return normalized
