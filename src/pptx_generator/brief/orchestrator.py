from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from .models import (
    BriefAIRecord,
    BriefCard,
    BriefDocument,
    BriefGenerationMeta,
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
        card_limit: int | None = None,
    ) -> tuple[BriefDocument, BriefGenerationMeta, list[BriefAIRecord]]:
        try:
            policy = self._policy_set.get_policy(policy_id)
        except BriefPolicyError as exc:
            raise BriefAIOrchestrationError(str(exc)) from exc

        cards = self._build_cards(source, policy, card_limit)
        story_context = self._build_story_context(source, policy)
        brief_id = source.meta.brief_id or f"brief-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        document = BriefDocument(brief_id=brief_id, cards=cards, story_context=story_context)
        meta = BriefGenerationMeta.from_document(
            document=document,
            policy_id=policy.id,
            source_payload=source.model_dump(mode="json"),
            cards_meta=[self._build_card_meta(card) for card in cards],
        )
        logs = [
            BriefAIRecord(
                card_id=card.card_id,
                prompt_template=policy.prompt_template_id or "brief.default",
                response_digest=card.message,
                warnings=["llm_stub"],
                tokens={"prompt": 0, "completion": 0, "total": 0},
            )
            for card in cards
        ]
        return document, meta, logs

    def _build_cards(
        self,
        source: BriefSourceDocument,
        policy: BriefPolicy,
        card_limit: int | None,
    ) -> list[BriefCard]:
        cards: list[BriefCard] = []
        chapters = source.chapters[: card_limit] if card_limit is not None else source.chapters
        if not chapters:
            logger.warning("Brief source に章がありません。ダミーカードを生成します。")
            dummy = self._build_dummy_card(policy, index=0)
            cards.append(dummy)
            return cards

        for index, chapter in enumerate(chapters):
            card = self._build_card_from_chapter(chapter, policy, index)
            cards.append(card)
        return cards

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
        return {
            "card_id": card.card_id,
            "intent_tags": card.intent_tags,
            "story_phase": card.story.phase,
            "content_hash": self._hash_card(card),
            "body_lines": len(card.narrative),
        }

    @staticmethod
    def _hash_card(card: BriefCard) -> str:
        payload = card.model_dump(mode="json", exclude_none=True)
        digest = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(digest.encode("utf-8")).hexdigest()
