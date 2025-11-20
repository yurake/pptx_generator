from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Literal, Sequence

from ..models import TemplateBlueprint, TemplateBlueprintSlide, TemplateBlueprintSlot
from .llm_client import PrepareLLMClient, PrepareLLMConfigurationError, PrepareLLMResult, create_prepare_llm_client
from .models import (
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
from .policy import PreparePolicy, PreparePolicyError, PreparePolicySet
from .prompts import build_prepare_prompt
from .source import PrepareSourceChapter, PrepareSourceDocument, PrepareSourceSupportingPoint

logger = logging.getLogger(__name__)

DEFAULT_PROMPT_ID = "prepare.default"
ALLOWED_STORY_PHASES = {"introduction", "problem", "solution", "impact", "next"}


class PrepareAIOrchestrationError(RuntimeError):
    """プレペア生成フローの例外。"""


class PrepareAIOrchestrator:
    """PrepareCard 生成オーケストレーター。"""

    def __init__(
        self,
        policy_set: PreparePolicySet,
        *,
        llm_client: PrepareLLMClient | None = None,
    ) -> None:
        self._policy_set = policy_set
        self._llm_client = llm_client or create_prepare_llm_client()

    def generate_document(
        self,
        source: PrepareSourceDocument,
        *,
        policy_id: str | None = None,
        page_limit: int | None = None,
        mode: Literal["dynamic", "static"] = "dynamic",
        blueprint: TemplateBlueprint | None = None,
        blueprint_ref: dict[str, str] | None = None,
    ) -> tuple[PrepareDocument, PrepareGenerationMeta, list[PrepareAIRecord]]:
        try:
            policy = self._policy_set.get_policy(policy_id)
        except PreparePolicyError as exc:
            raise PrepareAIOrchestrationError(str(exc)) from exc

        normalized_mode = (mode or "dynamic").lower()
        if normalized_mode not in {"dynamic", "static"}:
            normalized_mode = "dynamic"

        include_title_page = normalized_mode == "dynamic" and page_limit is None

        if normalized_mode == "static":
            if blueprint is None:
                raise PrepareAIOrchestrationError("static モードには Blueprint が必要です")
            cards, slot_summary, ai_records = self._build_cards_static(
                source=source,
                policy=policy,
                blueprint=blueprint,
                page_limit=page_limit,
            )
        else:
            cards, ai_records = self._build_cards_dynamic(
                source=source,
                policy=policy,
                page_limit=page_limit,
                include_title_page=include_title_page,
            )
            slot_summary = None

        story_context = self._build_story_context(cards=cards, source=source, policy=policy)
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
            policy_id=policy.id,
            source_payload=source.model_dump(mode="json"),
            cards_meta=[self._build_card_meta(card) for card in cards],
            mode=normalized_mode,  # type: ignore[arg-type]
            blueprint_path=blueprint_ref.get("path") if blueprint_ref else None,
            blueprint_hash=blueprint_ref.get("hash") if blueprint_ref else None,
            slot_summary=slot_summary,
            constraints=constraints,
        )
        return document, meta, ai_records

    def _build_cards_dynamic(
        self,
        *,
        source: PrepareSourceDocument,
        policy: PreparePolicy,
        page_limit: int | None,
        include_title_page: bool,
    ) -> tuple[list[PrepareCard], list[PrepareAIRecord]]:
        payload = self._build_dynamic_prompt_payload(
            source,
            policy=policy,
            page_limit=page_limit,
            include_title_page=include_title_page,
        )
        prompt = build_prepare_prompt(payload)
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
                policy=policy,
                generated_at=now,
                is_title_card=is_title_card,
                default_title=source.meta.title,
            )
            cards.append(card)

            ai_records.append(
                PrepareAIRecord(
                    card_id=card.card_id,
                    prompt_template=policy.prompt_template_id or DEFAULT_PROMPT_ID,
                    model=llm_result.model,
                    prompt_fragment=prompt[:200],
                    response_digest=json.dumps(entry, ensure_ascii=False)[:200],
                    warnings=llm_result.warnings + entry.get("warnings", []),
                    tokens=llm_result.tokens if index == 0 else {},
                )
            )

        if include_title_page and not any(card.content.title for card in cards):
            title_card = self._build_default_title_card(source=source, policy=policy, generated_at=now)
            cards.insert(0, title_card)
            ai_records.insert(
                0,
                PrepareAIRecord(
                    card_id=title_card.card_id,
                    prompt_template=policy.prompt_template_id or DEFAULT_PROMPT_ID,
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
        policy: PreparePolicy,
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
        policy: PreparePolicy,
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

        story_phase = str(entry.get("story_phase") or policy.resolve_story_phase(index)).lower()
        if story_phase not in ALLOWED_STORY_PHASES:
            story_phase = policy.resolve_story_phase(index)

        intent_tags_raw = entry.get("intent_tags")
        if isinstance(intent_tags_raw, list):
            intent_tags = [str(tag).strip() for tag in intent_tags_raw if str(tag).strip()]
        else:
            intent_tags = []
        if not intent_tags:
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
        blocks: list[PrepareBodyBlock] = []
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    block_type = str(item.get("type") or "paragraph").strip() or "paragraph"
                    text = item.get("text")
                    headers = item.get("headers")
                    rows = item.get("rows")
                    ref = item.get("ref")
                    description = item.get("description")
                    data = item.get("data")
                    items = item.get("items")
                    bullet_lines: list[str] = []
                    if isinstance(items, list):
                        for value in items:
                            if isinstance(value, str) and value.strip():
                                bullet_lines.append(value.strip())
                            elif isinstance(value, dict):
                                line = str(value.get("text") or "").strip()
                                if line:
                                    bullet_lines.append(line)
                    if block_type == "bullets" and bullet_lines and not text:
                        text = "\n".join(f"- {line}" for line in bullet_lines)

                    has_content = any(
                        [
                            isinstance(text, str) and text.strip(),
                            isinstance(headers, list) and any(str(h).strip() for h in headers),
                            isinstance(rows, list) and any(row for row in rows),
                            isinstance(description, str) and description.strip(),
                            isinstance(data, dict) and data,
                        ]
                    )
                    if not has_content:
                        continue
                    block = PrepareBodyBlock(
                        type=block_type,
                        text=text,
                        headers=headers,
                        rows=rows,
                        ref=ref,
                        description=description,
                        data=data,
                    )
                    blocks.append(block)
                elif isinstance(item, str) and item.strip():
                    blocks.append(PrepareBodyBlock(type="paragraph", text=item.strip()))
        elif isinstance(payload, dict):
            block_type = str(payload.get("type") or "paragraph").strip() or "paragraph"
            text = payload.get("text")
            headers = payload.get("headers")
            rows = payload.get("rows")
            ref = payload.get("ref")
            description = payload.get("description")
            data = payload.get("data")
            has_content = any(
                [
                    isinstance(text, str) and text.strip(),
                    isinstance(headers, list) and any(str(h).strip() for h in headers),
                    isinstance(rows, list) and any(row for row in rows),
                    isinstance(description, str) and description.strip(),
                    isinstance(data, dict) and data,
                ]
            )
            if has_content:
                blocks.append(
                    PrepareBodyBlock(
                        type=block_type,
                        text=text,
                        headers=headers,
                        rows=rows,
                        ref=ref,
                        description=description,
                        data=data,
                    )
                )
        elif isinstance(payload, str) and payload.strip():
            blocks.append(PrepareBodyBlock(type="paragraph", text=payload.strip()))

        if not blocks:
            blocks.append(PrepareBodyBlock(type="placeholder", text="内容を確認中"))
        return blocks

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
        policy: PreparePolicy,
        generated_at: datetime,
    ) -> PrepareCard:
        title_text = (source.meta.title or source.meta.prepare_id or "Proposal").strip()
        subtitle = source.meta.client
        body_blocks: list[PrepareBodyBlock] = []
        if source.meta.objective:
            body_blocks.append(PrepareBodyBlock(type="paragraph", text=source.meta.objective))

        role = PrepareCardRole(story_phase="introduction", intent_tags=["introduction"])
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
        policy: PreparePolicy,
        blueprint: TemplateBlueprint,
        page_limit: int | None,
    ) -> tuple[list[PrepareCard], dict[str, int], list[PrepareAIRecord]]:
        if page_limit is not None:
            raise PrepareAIOrchestrationError("static モードでは --page-limit オプションを使用できません")

        slot_entries: list[tuple[int, TemplateBlueprintSlide, TemplateBlueprintSlot]] = []
        for slide_index, blueprint_slide in enumerate(blueprint.slides):
            for slot_index, slot in enumerate(blueprint_slide.slots):
                slot_entries.append((len(slot_entries), blueprint_slide, slot))

        required_entries = [entry for entry in slot_entries if entry[2].required]
        optional_entries = [entry for entry in slot_entries if not entry[2].required]

        chapters = list(source.chapters)
        if len(chapters) < len(required_entries):
            msg = (
                "Blueprint の必須 slot 数を満たす章が不足しています: "
                f"required={len(required_entries)} actual={len(chapters)}"
            )
            raise PrepareAIOrchestrationError(msg)

        chapter_assignments: dict[int, PrepareSourceChapter] = {}
        chapter_iter_index = 0

        for entry in required_entries:
            if chapter_iter_index >= len(chapters):
                break
            chapter_assignments[entry[0]] = chapters[chapter_iter_index]
            chapter_iter_index += 1

        for entry in optional_entries:
            if chapter_iter_index >= len(chapters):
                break
            chapter_assignments[entry[0]] = chapters[chapter_iter_index]
            chapter_iter_index += 1

        cards: list[PrepareCard] = []
        required_fulfilled = 0
        optional_used = 0

        for order, blueprint_slide, slot in slot_entries:
            chapter = chapter_assignments.get(order)
            card = self._build_card_from_blueprint_slot(
                order=order,
                slide=blueprint_slide,
                slot=slot,
                chapter=chapter,
                policy=policy,
            )
            cards.append(card)

            blueprint_meta = card.meta.get("blueprint") if isinstance(card.meta, dict) else None
            fulfilled = bool(blueprint_meta.get("fulfilled")) if isinstance(blueprint_meta, dict) else False
            if slot.required:
                if fulfilled:
                    required_fulfilled += 1
            else:
                if fulfilled:
                    optional_used += 1

        slot_summary = {
            "required_total": len(required_entries),
            "required_fulfilled": required_fulfilled,
            "optional_total": len(optional_entries),
            "optional_used": optional_used,
        }
        ai_records = [
            PrepareAIRecord(
                card_id="batch",
                prompt_template=DEFAULT_PROMPT_ID,
                model="mock-local",
                response_digest=f"cards={len(cards)} mode=static",
                warnings=["blueprint_stub"],
                tokens={},
            )
        ]
        return cards, slot_summary, ai_records

    def _build_card_from_blueprint_slot(
        self,
        *,
        order: int,
        slide: TemplateBlueprintSlide,
        slot: TemplateBlueprintSlot,
        chapter: PrepareSourceChapter | None,
        policy: PreparePolicy,
    ) -> PrepareCard:
        story_phase = policy.resolve_story_phase(order)
        intent_tags: list[str]
        subtitle: str | None = None
        if chapter is not None:
            intent_tags = chapter.intent_tags or slot.intent_tags or []
            title = policy.resolve_chapter_title(order, chapter.title or slide.layout)
            headline = chapter.message or chapter.title or chapter.id
            body_blocks = self._build_chapter_body_blocks(chapter)
            notes = self._build_chapter_notes(chapter.supporting_points)
            meta_source = {
                "id": chapter.id,
                "title": chapter.title,
            }
            subtitle = chapter.title
            fulfilled = True
        else:
            intent_tags = slot.intent_tags or [story_phase]
            title = policy.resolve_chapter_title(order, slide.layout or slot.slot_id)
            headline = f"{slide.layout} - {slot.anchor}" if slide.layout else slot.slot_id
            body_blocks = [
                PrepareBodyBlock(
                    type="placeholder",
                    text=f"Slot {slot.slot_id} に対応する章がまだ割り当てられていません",
                )
            ]
            notes = []
            meta_source = None
            subtitle = slide.layout
            fulfilled = False

        if not intent_tags:
            intent_tags = [story_phase]

        role = PrepareCardRole(story_phase=story_phase, intent_tags=intent_tags)

        is_title_slot = (order == 0) and (
            (slide.layout and slide.layout.lower() == "title")
            or slot.slot_id.lower().startswith("title")
        )
        if is_title_slot:
            content = PrepareCardContent(title=title, subtitle=subtitle, body=body_blocks, notes=notes)
        else:
            headline_text = headline or title
            content = PrepareCardContent(headline=headline_text, subtitle=subtitle, body=body_blocks, notes=notes)

        blueprint_meta = {
            "slide_id": slide.slide_id,
            "layout": slide.layout,
            "slot_id": slot.slot_id,
            "anchor": slot.anchor,
            "content_type": slot.content_type,
            "required": slot.required,
            "fulfilled": fulfilled,
            "intent_tags": slot.intent_tags,
        }

        meta: dict[str, Any] = {
            "mode": "static",
            "blueprint": blueprint_meta,
        }
        if meta_source:
            meta["source_chapter"] = meta_source

        return PrepareCard(
            card_id=self._normalize_slot_card_id(slot.slot_id),
            order=order + 1,
            role=role,
            content=content,
            meta=meta,
        )

    @staticmethod
    def _normalize_slot_card_id(slot_id: str) -> str:
        normalized = slot_id.lower().replace("/", "-").replace(".", "-")
        normalized = normalized.replace(" ", "-")
        filtered = [ch for ch in normalized if ch.isalnum() or ch in {"-"}]
        result = "".join(filtered)
        return result or "slot"

    def _build_dummy_card(self, policy: PreparePolicy, index: int) -> PrepareCard:
        story_phase = policy.resolve_story_phase(index)
        heading_text = story_phase.title() if isinstance(story_phase, str) else str(story_phase)
        role = PrepareCardRole(story_phase=story_phase, intent_tags=[story_phase])
        is_title_card = index == 0
        headline_text = "自動生成されたプレペアカード（ダミー）"
        content = PrepareCardContent(
            title=heading_text if is_title_card else None,
            headline=None if is_title_card else headline_text,
            body=[
                PrepareBodyBlock(
                    type="paragraph",
                    text="入力プレペアが空だったため、ダミーカードを生成しました。",
                )
            ],
            notes=[PrepareNoteEntry(type="note", text="原稿が空だったために生成されたダミーです")],
        )
        return PrepareCard(card_id="intro-01", order=index + 1, role=role, content=content, meta={})

    def _build_story_context(
        self,
        *,
        cards: Sequence[PrepareCard],
        source: PrepareSourceDocument,
        policy: PreparePolicy,
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
        elif policy.chapters:
            for chapter in policy.chapters:
                chapters.append(
                    {
                        "id": chapter.id,
                        "title": chapter.title,
                        "description": chapter.description,
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
