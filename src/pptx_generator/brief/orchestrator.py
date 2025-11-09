from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal

from ..models import TemplateBlueprint, TemplateBlueprintSlide, TemplateBlueprintSlot
from .models import (
    BriefAIRecord,
    BriefCard,
    BriefDocument,
    BriefGenerationMeta,
    BriefStatusType,
    BriefStoryContext,
    BriefStoryInfo,
)
from .policy import BriefPolicy, BriefPolicyError, BriefPolicySet
from .source import BriefSourceChapter, BriefSourceDocument

logger = logging.getLogger(__name__)


class BriefAIOrchestrationError(RuntimeError):
    """ブリーフ生成フローの例外。"""


class BriefAIOrchestrator:
    """BriefCard 生成オーケストレーター。"""

    def __init__(self, policy_set: BriefPolicySet) -> None:
        self._policy_set = policy_set

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
            cards, slot_summary = self._build_cards_static(
                source,
                policy,
                blueprint,
                page_limit=page_limit,
            )
        else:
            cards = self._build_cards(source, policy, page_limit)
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
        batch_record = BriefAIRecord(
            card_id="batch",
            prompt_template=policy.prompt_template_id or "brief.batch",
            response_digest=f"cards={len(cards)} mode={mode}",
            warnings=["llm_stub"],
            tokens={"prompt": 0, "completion": 0, "total": 0},
            batch_card_ids=[card.card_id for card in cards],
        )
        return document, meta, [batch_record]

    def _build_cards(
        self,
        source: BriefSourceDocument,
        policy: BriefPolicy,
        page_limit: int | None,
    ) -> list[BriefCard]:
        cards: list[BriefCard] = []
        chapters = source.chapters[: page_limit] if page_limit is not None else source.chapters
        if not chapters:
            logger.warning("Brief source に章がありません。ダミーカードを生成します。")
            dummy = self._build_dummy_card(policy, index=0)
            cards.append(dummy)
            return cards

        for index, chapter in enumerate(chapters):
            card = self._build_card_from_chapter(chapter, policy, index)
            cards.append(card)
        return cards

    def _build_cards_static(
        self,
        source: BriefSourceDocument,
        policy: BriefPolicy,
        blueprint: TemplateBlueprint,
        *,
        page_limit: int | None,
    ) -> tuple[list[BriefCard], dict[str, int]]:
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

        # 必須 slot へ優先的に割り当て
        for entry in required_entries:
            if chapter_iter_index >= len(chapters):
                break
            chapter_assignments[entry[0]] = chapters[chapter_iter_index]
            chapter_iter_index += 1

        # 残った章を任意 slot へ割り当て
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
            cards.append(card)

        slot_summary = {
            "required_total": len(required_entries),
            "required_fulfilled": required_fulfilled,
            "optional_total": len(optional_entries),
            "optional_used": optional_used,
        }

        if required_fulfilled < len(required_entries):
            missing = len(required_entries) - required_fulfilled
            msg = f"必須 slot に対応するカードが不足しています: missing={missing}"
            raise BriefAIOrchestrationError(msg)

        return cards, slot_summary

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
        }
        blueprint_slot_meta["fulfilled"] = slot_fulfilled

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
        chapter_title = policy.resolve_chapter_title(index, "イントロダクション")
        story_phase = policy.resolve_story_phase(index)
        story = BriefStoryInfo(phase=story_phase, goal="ブリーフの骨子を示す")
        return BriefCard(
            card_id="intro-01",
            chapter=chapter_title,
            message="自動生成されたブリーフカード（ダミー）",
            narrative=["入力ブリーフが空だったため、ダミーカードを生成しました。"],
            supporting_points=[],
            story=story,
            intent_tags=["introduction"],
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
        meta = {
            "card_id": card.card_id,
            "intent_tags": card.intent_tags,
            "story_phase": card.story.phase,
            "content_hash": self._hash_card(card),
            "body_lines": len(card.narrative),
        }
        if card.slot_id:
            meta.update(
                {
                    "slide_id": card.slide_id,
                    "slot_id": card.slot_id,
                    "required": card.required,
                    "slot_fulfilled": card.slot_fulfilled,
                }
            )
        return meta

    @staticmethod
    def _hash_card(card: BriefCard) -> str:
        payload = card.model_dump(mode="json", exclude_none=True)
        digest = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(digest.encode("utf-8")).hexdigest()
