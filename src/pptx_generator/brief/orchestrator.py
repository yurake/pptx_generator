from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from ..models import TemplateBlueprint, TemplateBlueprintSlide, TemplateBlueprintSlot
from .llm_client import BriefLLMClient, BriefLLMConfigurationError, BriefLLMResult, create_brief_llm_client
from .models import (
    BriefAIRecord,
    BriefCard,
    BriefCardMeta,
    BriefDocument,
    BriefGenerationMeta,
    BriefStatusType,
    BriefStoryContext,
    BriefStoryInfo,
    BriefEvidence,
    BriefSupportingPoint,
)
from .policy import BriefPolicy, BriefPolicyError, BriefPolicySet
from .prompts import build_brief_prompt
from .source import BriefSourceChapter, BriefSourceDocument

logger = logging.getLogger(__name__)

DEFAULT_PROMPT_ID = "brief.default"
ALLOWED_STORY_PHASES = {"introduction", "problem", "solution", "impact", "next"}


class BriefAIOrchestrationError(RuntimeError):
    """ブリーフ生成フローの例外。"""


class BriefAIOrchestrator:
    """BriefCard 生成オーケストレーター。"""

    def __init__(
        self,
        policy_set: BriefPolicySet,
        *,
        llm_client: BriefLLMClient | None = None,
    ) -> None:
        self._policy_set = policy_set
        self._llm_client = llm_client or create_brief_llm_client()

    def generate_document(
        self,
        source: BriefSourceDocument,
        *,
        policy_id: str | None = None,
        page_limit: int | None = None,
        all_cards_status: BriefStatusType | None = None,
        mode: Literal["dynamic", "static"] = "dynamic",
        blueprint: TemplateBlueprint | None = None,
        blueprint_ref: dict[str, str] | None = None,
    ) -> tuple[BriefDocument, BriefGenerationMeta, list[BriefAIRecord]]:
        try:
            policy = self._policy_set.get_policy(policy_id)
        except BriefPolicyError as exc:
            raise BriefAIOrchestrationError(str(exc)) from exc

        normalized_mode = (mode or "dynamic").lower()
        if normalized_mode not in {"dynamic", "static"}:
            normalized_mode = "dynamic"

        if normalized_mode == "static":
            if blueprint is None:
                raise BriefAIOrchestrationError("static モードには Blueprint が必要です")
            cards, slot_summary, ai_records = self._build_cards_static(
                source=source,
                policy=policy,
                blueprint=blueprint,
                page_limit=page_limit,
                all_cards_status=all_cards_status,
            )
        else:
            cards, ai_records = self._build_cards_dynamic(
                source=source,
                policy=policy,
                page_limit=page_limit,
                all_cards_status=all_cards_status,
            )
            slot_summary = None

        if all_cards_status is not None:
            for card in cards:
                card.status = all_cards_status

        story_context = self._build_story_context(source, policy)
        brief_id = source.meta.brief_id or f"brief-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        document = BriefDocument(brief_id=brief_id, cards=cards, story_context=story_context)
        meta = BriefGenerationMeta.from_document(
            document=document,
            policy_id=policy.id,
            source_payload=source.model_dump(mode="json"),
            cards_meta=[self._build_card_meta(card) for card in cards],
            mode=normalized_mode,  # type: ignore[arg-type]
            blueprint_path=blueprint_ref.get("path") if blueprint_ref else None,
            blueprint_hash=blueprint_ref.get("hash") if blueprint_ref else None,
            slot_summary=slot_summary,
        )
        return document, meta, ai_records

    def _build_cards_dynamic(
        self,
        *,
        source: BriefSourceDocument,
        policy: BriefPolicy,
        page_limit: int | None,
        all_cards_status: BriefStatusType | None,
    ) -> tuple[list[BriefCard], list[BriefAIRecord]]:
        payload = self._build_prompt_payload(source, page_limit=page_limit)
        prompt = build_brief_prompt(payload)
        try:
            llm_result = self._llm_client.generate(prompt, model_hint=None)
        except BriefLLMConfigurationError as exc:
            raise BriefAIOrchestrationError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise BriefAIOrchestrationError(f"LLM 呼び出しに失敗しました: {exc}") from exc

        data = self._parse_llm_output(llm_result)
        chapters_payload = data.get("chapters")
        if not isinstance(chapters_payload, list) or not chapters_payload:
            raise BriefAIOrchestrationError("LLM 応答に 'chapters' 配列が含まれていません")

        if page_limit is not None:
            chapters_payload = chapters_payload[:page_limit]

        now = datetime.now(timezone.utc)
        cards: list[BriefCard] = []
        ai_records: list[BriefAIRecord] = []

        for index, entry in enumerate(chapters_payload):
            card = self._build_card_from_llm_entry(
                entry,
                index=index,
                policy=policy,
                objective=source.meta.objective,
                generated_at=now,
                default_status=all_cards_status or "draft",
            )
            cards.append(card)

            ai_records.append(
                BriefAIRecord(
                    card_id=card.card_id,
                    prompt_template=policy.prompt_template_id or DEFAULT_PROMPT_ID,
                    model=llm_result.model,
                    prompt_fragment=prompt[:200],
                    response_digest=json.dumps(entry, ensure_ascii=False)[:200],
                    warnings=llm_result.warnings + entry.get("warnings", []),
                    tokens=llm_result.tokens if index == 0 else {},
                )
            )

        return cards, ai_records

    def _build_prompt_payload(
        self,
        source: BriefSourceDocument,
        *,
        page_limit: int | None,
    ) -> dict[str, Any]:
        chapters = source.chapters[: page_limit] if page_limit is not None else list(source.chapters)
        chapter_payloads: list[dict[str, Any]] = []
        for chapter in chapters:
            supporting_points_payload: list[dict[str, Any]] = []
            for item in getattr(chapter, "supporting_points", []) or []:
                evidence_obj = getattr(item, "evidence", None)
                if evidence_obj is None:
                    evidence_type = getattr(item, "evidence_type", None)
                    evidence_value = getattr(item, "evidence_value", None)
                    if evidence_type and evidence_value:
                        evidence_obj = BriefEvidence(type=evidence_type, value=evidence_value)

                evidence_payload = None
                if evidence_obj is not None:
                    evidence_payload = {
                        "type": evidence_obj.type,
                        "value": evidence_obj.value,
                    }

                supporting_points_payload.append(
                    {
                        "statement": getattr(item, "statement", ""),
                        "evidence": evidence_payload,
                    }
                )

            chapter_payloads.append(
                {
                    "title": chapter.title,
                    "message": chapter.message,
                    "details": chapter.details,
                    "supporting_points": supporting_points_payload,
                    "intent_tags": chapter.intent_tags,
                }
            )
        return {
            "meta": {
                "title": source.meta.title,
                "client": source.meta.client,
                "objective": source.meta.objective,
            },
            "chapters": chapter_payloads,
        }

    def _parse_llm_output(self, result: BriefLLMResult) -> dict[str, Any]:
        text = result.text.strip()
        if not text:
            raise BriefAIOrchestrationError("LLM 応答が空でした")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning("LLM 応答の JSON 解析に失敗: %s", exc)
            raise BriefAIOrchestrationError("LLM 応答を JSON として解析できませんでした") from exc

    def _build_card_from_llm_entry(
        self,
        entry: dict[str, Any],
        *,
        index: int,
        policy: BriefPolicy,
        objective: str | None,
        generated_at: datetime,
        default_status: BriefStatusType,
    ) -> BriefCard:
        title = str(entry.get("title") or f"Chapter {index + 1}")
        card_id = str(entry.get("card_id") or self._slugify(title) or f"chapter-{index + 1}")

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

        message = str(entry.get("message") or title)

        narrative_raw = entry.get("narrative")
        if isinstance(narrative_raw, list):
            narrative_candidates = [str(item).strip() for item in narrative_raw if str(item).strip()]
        elif isinstance(narrative_raw, str):
            narrative_candidates = [narrative_raw.strip()]
        else:
            narrative_candidates = []
        narrative = self._normalize_narrative(narrative_candidates)

        supporting_raw = entry.get("supporting_points") or []
        supporting_points = self._build_supporting_points(supporting_raw, narrative)

        story = BriefStoryInfo(
            phase=story_phase,
            goal=objective,
        )

        return BriefCard(
            card_id=card_id,
            chapter=title,
            message=message,
            narrative=narrative,
            supporting_points=supporting_points,
            story=story,
            intent_tags=intent_tags,
            status=default_status,
            meta=BriefCardMeta(updated_at=generated_at),
        )

    def _build_supporting_points(
        self,
        payload: Any,
        narrative: list[str],
    ) -> list[BriefSupportingPoint]:
        items: list[BriefSupportingPoint] = []
        if isinstance(payload, list):
            for entry in payload:
                if isinstance(entry, dict):
                    statement = str(entry.get("statement") or "").strip()
                    if not statement:
                        continue
                    evidence_payload = entry.get("evidence")
                    evidence = None
                    if isinstance(evidence_payload, dict):
                        ev_type = evidence_payload.get("type")
                        ev_value = evidence_payload.get("value")
                        if isinstance(ev_type, str) and isinstance(ev_value, str):
                            evidence = BriefEvidence(type=ev_type, value=ev_value)
                    items.append(BriefSupportingPoint(statement=statement, evidence=evidence))
                elif isinstance(entry, str) and entry.strip():
                    items.append(BriefSupportingPoint(statement=entry.strip()))
        if not items:
            items = [BriefSupportingPoint(statement=line) for line in narrative]
        return items[: len(narrative) or len(items)]

    def _normalize_narrative(self, candidates: list[str]) -> list[str]:
        max_lines = 6
        max_chars = 40
        normalized: list[str] = []
        for text in candidates:
            if len(normalized) >= max_lines:
                break
            stripped = text.strip()
            if not stripped:
                continue
            if len(stripped) > max_chars:
                stripped = stripped[: max_chars]
            normalized.append(stripped)
        if not normalized:
            normalized.append("内容を確認中")
        return normalized

    def _build_cards_static(
        self,
        *,
        source: BriefSourceDocument,
        policy: BriefPolicy,
        blueprint: TemplateBlueprint,
        page_limit: int | None,
        all_cards_status: BriefStatusType | None,
    ) -> tuple[list[BriefCard], dict[str, int], list[BriefAIRecord]]:
        if page_limit is not None:
            raise BriefAIOrchestrationError("static モードでは --page-limit オプションを使用できません")

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
            raise BriefAIOrchestrationError(msg)

        chapter_assignments: dict[int, BriefSourceChapter] = {}
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

        cards: list[BriefCard] = []
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
            if slot.required:
                if chapter is not None:
                    required_fulfilled += 1
            else:
                if chapter is not None:
                    optional_used += 1
            if all_cards_status is not None:
                card.status = all_cards_status
            cards.append(card)

        slot_summary = {
            "required_total": len(required_entries),
            "required_fulfilled": required_fulfilled,
            "optional_total": len(optional_entries),
            "optional_used": optional_used,
        }
        ai_records = [
            BriefAIRecord(
                card_id="batch",
                prompt_template=DEFAULT_PROMPT_ID,
                model="mock-local",
                response_digest=f"cards={len(cards)} mode=static",
                warnings=["blueprint_stub"],
                tokens={},
            )
        ]
        return cards, slot_summary, ai_records

    def _build_card_from_chapter(
        self,
        chapter: BriefSourceChapter,
        policy: BriefPolicy,
        index: int,
    ) -> BriefCard:
        story_phase = policy.resolve_story_phase(index)
        chapter_title = policy.resolve_chapter_title(index, chapter.title)
        supporting_points = [item.to_brief_supporting_point() for item in chapter.supporting_points]
        narrative = chapter.details or []
        if not narrative and chapter.message:
            narrative = [chapter.message]
        story = BriefStoryInfo(
            phase=story_phase, goal=None, tension=None, resolution=None
        )
        return BriefCard(
            card_id=f"{chapter.id}",
            chapter=chapter_title,
            message=chapter.message or chapter.title,
            narrative=narrative,
            supporting_points=supporting_points,
            story=story,
            intent_tags=chapter.intent_tags,
            status="draft",
        )

    def _build_card_from_blueprint_slot(
        self,
        *,
        order: int,
        slide: TemplateBlueprintSlide,
        slot: TemplateBlueprintSlot,
        chapter: BriefSourceChapter | None,
        policy: BriefPolicy,
    ) -> BriefCard:
        story_phase = policy.resolve_story_phase(order)
        if chapter is not None:
            chapter_title = policy.resolve_chapter_title(order, chapter.title or slide.layout)
            message = chapter.message or chapter.title or chapter.id
            narrative = list(chapter.details) if chapter.details else []
            if not narrative and chapter.message:
                narrative = [chapter.message]
            supporting_points = [item.to_brief_supporting_point() for item in chapter.supporting_points]
            intent_tags = chapter.intent_tags or slot.intent_tags or []
            slot_fulfilled = True
        else:
            chapter_title = policy.resolve_chapter_title(order, slide.layout or slot.slot_id)
            message = f"{slide.layout} - {slot.anchor}" if slide.layout else slot.slot_id
            narrative = []
            supporting_points = []
            intent_tags = slot.intent_tags or []
            slot_fulfilled = False

        story = BriefStoryInfo(phase=story_phase, goal=None, tension=None, resolution=None)
        card_id = self._normalize_slot_card_id(slot.slot_id)
        blueprint_slot_meta: dict[str, Any] = {
            "anchor": slot.anchor,
            "content_type": slot.content_type,
            "intent_tags": slot.intent_tags,
            "fulfilled": slot_fulfilled,
        }

        return BriefCard(
            card_id=card_id,
            chapter=chapter_title,
            message=message,
            narrative=narrative,
            supporting_points=supporting_points,
            story=story,
            intent_tags=intent_tags,
            status="draft",
            layout_mode="static",
            slide_id=slide.slide_id,
            slot_id=slot.slot_id,
            required=slot.required,
            slot_fulfilled=slot_fulfilled,
            blueprint_slot=blueprint_slot_meta,
        )

    @staticmethod
    def _normalize_slot_card_id(slot_id: str) -> str:
        normalized = slot_id.lower().replace("/", "-").replace(".", "-")
        normalized = normalized.replace(" ", "-")
        filtered = [ch for ch in normalized if ch.isalnum() or ch in {"-"}]
        result = "".join(filtered)
        return result or "slot"

    def _build_dummy_card(self, policy: BriefPolicy, index: int) -> BriefCard:
        chapter_title = policy.resolve_story_phase(index)
        story_phase = policy.resolve_story_phase(index)
        story = BriefStoryInfo(phase=story_phase, goal="ブリーフの骨子を示す")
        return BriefCard(
            card_id="intro-01",
            chapter=chapter_title,
            message="自動生成されたブリーフカード（ダミー）",
            narrative=["入力ブリーフが空だったため、ダミーカードを生成しました。"],
            supporting_points=[],
            story=story,
            intent_tags=[story_phase],
            status="draft",
        )

    def _build_story_context(self, source: BriefSourceDocument, policy: BriefPolicy) -> BriefStoryContext:
        chapters = []
        if policy.chapters:
            for chapter in policy.chapters:
                chapters.append(
                    {
                        "id": chapter.id,
                        "title": chapter.title,
                        "description": None,
                    }
                )
        elif source.chapters:
            for chapter in source.chapters:
                chapters.append(
                    {
                        "id": chapter.id,
                        "title": chapter.title,
                        "description": None,
                    }
                )
        return BriefStoryContext.model_validate(
            {
                "chapters": chapters,
                "tone": None,
                "must_have_messages": [],
            }
        )

    def _build_card_meta(self, card: BriefCard) -> dict[str, Any]:
        payload = {
            "card_id": card.card_id,
            "intent_tags": card.intent_tags,
            "story_phase": card.story.phase,
            "content_hash": self._hash_card(card),
            "body_lines": len(card.narrative),
        }
        if card.slot_id:
            payload.update(
                {
                    "slide_id": card.slide_id,
                    "slot_id": card.slot_id,
                    "required": card.required,
                    "slot_fulfilled": card.slot_fulfilled,
                }
            )
        return payload

    @staticmethod
    def _hash_card(card: BriefCard) -> str:
        payload = card.model_dump(mode="json", exclude_none=True)
        digest = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(digest.encode("utf-8")).hexdigest()

    @staticmethod
    def _slugify(value: str) -> str:
        normalized = value.lower()
        normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
        normalized = normalized.strip("-")
        return normalized
