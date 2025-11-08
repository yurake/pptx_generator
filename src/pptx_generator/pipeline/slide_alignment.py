"""BriefCard と JobSpec の ID 整合を担うユーティリティ。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable, Literal

from ..brief.models import BriefCard, BriefDocument
from ..content_ai import (LLMClient, SlideMatchCandidate,
                          SlideMatchRequest, SlideMatchResponse,
                          create_llm_client)
from ..models import ContentApprovalDocument, ContentSlide, JobSpec, Slide

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SlideAlignmentRecord:
    """カード単位の整合結果。"""

    card_id: str
    recommended_slide_id: str | None
    confidence: float
    reason: str | None
    status: Literal["applied", "pending", "fallback", "skipped"]
    candidates: tuple[str, ...] = ()


@dataclass(slots=True)
class SlideAlignmentResult:
    """整合処理全体の結果。"""

    document: ContentApprovalDocument
    records: list[SlideAlignmentRecord]
    meta: dict[str, object]


@dataclass(slots=True)
class SlideIdAlignerOptions:
    """整合処理の設定。"""

    confidence_threshold: float = 0.6
    max_candidates: int = 12


class SlideIdAligner:
    """BriefCard ↔ JobSpec の ID 整合を担当するクラス。"""

    def __init__(
        self,
        options: SlideIdAlignerOptions | None = None,
        *,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._options = options or SlideIdAlignerOptions()
        self._client = llm_client or create_llm_client()

    def align(
        self,
        *,
        spec: JobSpec,
        brief_document: BriefDocument | None,
        content_document: ContentApprovalDocument,
    ) -> SlideAlignmentResult:
        if brief_document is None or not brief_document.cards:
            logger.info("SlideIdAligner: brief_document が無いため整合処理をスキップします")
            return SlideAlignmentResult(
                document=content_document,
                records=[],
                meta={
                    "status": "skipped",
                    "reason": "brief_document_absent",
                },
            )

        card_map = {card.card_id: card for card in brief_document.cards}
        candidate_slides = list(spec.slides)
        if not candidate_slides:
            logger.warning("SlideIdAligner: JobSpec にスライドが存在しません")
            return SlideAlignmentResult(
                document=content_document,
                records=[],
                meta={
                    "status": "skipped",
                    "reason": "jobspec_empty",
                },
            )

        slide_assignments: dict[str, int] = {}
        records: list[SlideAlignmentRecord] = []

        for slide in content_document.slides:
            original_id = slide.id
            card = card_map.get(original_id)
            if card is None:
                logger.debug("SlideIdAligner: card_id=%s が brief_document に見つかりません", original_id)
                records.append(
                    SlideAlignmentRecord(
                        card_id=original_id,
                        recommended_slide_id=None,
                        confidence=0.0,
                        reason="card_not_found",
                        status="pending",
                    )
                )
                continue

            candidates = self._select_candidates(card, candidate_slides)
            match_request = self._build_match_request(card, candidates)
            response = self._client.match_slide(match_request)

            candidate_ids = tuple(candidate.id for candidate in candidates)
            record = SlideAlignmentRecord(
                card_id=card.card_id,
                recommended_slide_id=response.slide_id,
                confidence=response.confidence,
                reason=response.reason,
                status="pending",
                candidates=candidate_ids,
            )

            recommended_slide_id = response.slide_id
            if recommended_slide_id and recommended_slide_id not in record.candidates:
                recommended_slide_id = None
                record.recommended_slide_id = None

            if recommended_slide_id and response.confidence >= self._options.confidence_threshold:
                previous_index = slide_assignments.get(recommended_slide_id)
                if previous_index is None:
                    record.status = "applied"
                    slide_assignments[recommended_slide_id] = len(records)
                else:
                    previous_record = records[previous_index]
                    if response.confidence > previous_record.confidence:
                        previous_record.recommended_slide_id = None
                        previous_record.status = "pending"
                        previous_record.reason = (previous_record.reason or "") + " | reassigned"
                        record.status = "applied"
                        slide_assignments[recommended_slide_id] = len(records)
                    else:
                        record.status = "pending"
                        record.reason = (record.reason or "") + " | lower_than_existing"
                        record.recommended_slide_id = None
            records.append(record)

        assigned_slides = {slide_id for slide_id in slide_assignments}
        fallback_applied = 0
        for index, record in enumerate(records):
            if record.status == "applied" and record.recommended_slide_id:
                continue
            if not record.candidates:
                continue
            for candidate_id in record.candidates:
                if candidate_id not in assigned_slides:
                    record.recommended_slide_id = candidate_id
                    record.status = "fallback"
                    record.reason = (record.reason or "") + " | fallback_candidate"
                    assigned_slides.add(candidate_id)
                    slide_assignments[candidate_id] = index
                    fallback_applied += 1
                    break

        updated_slides: list[ContentSlide] = []
        applied = 0
        for slide in content_document.slides:
            original_id = slide.id
            record = next((entry for entry in records if entry.card_id == original_id), None)
            if record and record.recommended_slide_id:
                updated_slides.append(slide.model_copy(update={"id": record.recommended_slide_id}))
                if record.status in {"applied", "fallback"}:
                    applied += 1
            else:
                updated_slides.append(slide)

        aligned_document = content_document.model_copy(update={"slides": updated_slides})
        meta = {
            "status": "completed",
            "threshold": self._options.confidence_threshold,
            "cards_total": len(content_document.slides),
            "applied": applied,
            "fallback": fallback_applied,
            "pending": sum(1 for record in records if record.status not in {"applied", "fallback"}),
        }
        logger.info(
            "SlideIdAligner: cards_total=%d applied=%d pending=%d threshold=%.2f",
            meta["cards_total"],
            meta["applied"],
            meta["pending"],
            meta["threshold"],
        )
        return SlideAlignmentResult(document=aligned_document, records=records, meta=meta)

    def _build_match_request(
        self,
        card: BriefCard,
        candidates: list[Slide],
    ) -> SlideMatchRequest:
        summary_lines = []
        if card.message:
            summary_lines.append(card.message)
        summary_lines.extend(card.narrative[:3])
        summary_lines.extend(point.statement for point in card.supporting_points[:3])
        card_summary = "\n".join(line.strip() for line in summary_lines if line.strip()) or card.message

        candidate_entries: list[str] = []
        candidate_models: list[SlideMatchCandidate] = []
        for index, candidate in enumerate(candidates, start=1):
            candidate_entries.append(
                f"{index}. slide_id={candidate.id} layout={candidate.layout} title={candidate.title or ''}"
            )
            candidate_models.append(
                SlideMatchCandidate(
                    slide_id=candidate.id,
                    title=candidate.title,
                    layout=candidate.layout,
                    subtitle=candidate.subtitle,
                    notes=candidate.notes,
                )
            )

        prompt_parts = [
            "# カード情報",
            f"card_id: {card.card_id}",
            f"chapter: {card.chapter}",
            f"story_phase: {card.story.phase}",
            f"intent_tags: {', '.join(card.intent_tags) if card.intent_tags else 'なし'}",
            "summary:",
            card_summary,
            "",
            "# 候補スライド一覧",
            *candidate_entries,
            "",
            "以下の JSON 形式で回答してください:",
            '{"card_id": "' + card.card_id + '", "recommended_slide_id": "...", "confidence": 0.0～1.0, "reason": "..."}',
        ]
        prompt = "\n".join(prompt_parts)
        system_prompt = (
            "あなたはスライド構成のアシスタントです。カードの意図とテンプレート情報を比較し、最も適切な slide_id を1つだけ選んでください。"
        )

        return SlideMatchRequest(
            card_id=card.card_id,
            card_chapter=card.chapter,
            card_intent=tuple(card.intent_tags),
            card_story_phase=card.story.phase,
            card_summary=card_summary,
            prompt=prompt,
            system_prompt=system_prompt,
            candidates=candidate_models,
        )

    def _select_candidates(self, card: BriefCard, candidates: Iterable[Slide]) -> list[Slide]:
        scored: list[tuple[float, Slide]] = []
        for slide in candidates:
            score = self._heuristic_score(card, slide)
            scored.append((score, slide))
        scored.sort(key=lambda item: item[0], reverse=True)
        limited = [slide for _, slide in scored[: self._options.max_candidates]]
        if not limited:
            return list(candidates)[: self._options.max_candidates]
        return limited

    @staticmethod
    def _heuristic_score(card: BriefCard, slide: Slide) -> float:
        score = 0.0
        if slide.id == card.card_id:
            score += 5.0
        title = (slide.title or "").lower()
        chapter = card.chapter.lower()
        if chapter and chapter in title:
            score += 3.0
        if card.story.phase and card.story.phase.lower() in (slide.layout or "").lower():
            score += 1.5
        if card.intent_tags:
            for intent in card.intent_tags:
                if intent.lower() in title:
                    score += 1.0
        if slide.notes:
            ratio = SequenceMatcher(None, card.message.lower(), slide.notes.lower()).ratio()
            score += ratio * 2.0
        else:
            ratio = SequenceMatcher(None, card.message.lower(), title).ratio()
            score += ratio * 2.0
        return score
