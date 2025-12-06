"""PrepareCard と JobSpec の ID 整合を担うユーティリティ。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable, Literal

from ..prepare.models import PrepareCard, PrepareDocument
from ..slide_ai import (LLMClient, SlideMatchCandidate, SlideMatchRequest,
                        SlideMatchResponse, create_llm_client)
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
    """PrepareCard ↔ JobSpec の ID 整合を担当するクラス。"""

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
        prepare_document: PrepareDocument | None,
        content_document: ContentApprovalDocument,
    ) -> SlideAlignmentResult:
        if prepare_document is None or not prepare_document.cards:
            logger.info("SlideIdAligner: prepare_document が無いため整合処理をスキップします")
            return self._build_skip_result(content_document, "prepare_document_absent")

        card_map = {card.card_id: card for card in prepare_document.cards}
        candidate_slides = list(spec.slides)
        if not candidate_slides:
            logger.warning("SlideIdAligner: JobSpec にスライドが存在しません")
            return self._build_skip_result(content_document, "jobspec_empty")

        relevant_spec_ids = {
            candidate.id for candidate in candidate_slides if candidate.id in card_map
        }
        slide_assignments: dict[str, int] = {}
        records: list[SlideAlignmentRecord] = []

        for slide in content_document.slides:
            record = self._process_content_slide(
                slide=slide,
                card_map=card_map,
                candidate_slides=candidate_slides,
                slide_assignments=slide_assignments,
                records=records,
            )
            records.append(record)

        fallback_applied = self._apply_fallback_assignments(records, slide_assignments)
        updated_slides, applied = self._build_aligned_slides(content_document, records)
        unmatched_spec_slides = self._collect_unmatched_spec_slides(
            relevant_spec_ids, slide_assignments
        )
        records.extend(self._build_unmatched_records(unmatched_spec_slides))

        aligned_document = content_document.model_copy(update={"slides": updated_slides})
        meta = self._build_alignment_meta(
            content_document=content_document,
            relevant_spec_ids=relevant_spec_ids,
            unmatched_spec_slides=unmatched_spec_slides,
            applied=applied,
            fallback=fallback_applied,
            pending=sum(1 for record in records if record.status == "pending"),
        )
        logger.info(
            "SlideIdAligner: cards_total=%d jobspec_total=%d jobspec_unassigned=%d applied=%d pending=%d threshold=%.2f",
            meta["cards_total"],
            meta["jobspec_total"],
            meta["jobspec_unassigned"],
            meta["applied"],
            meta["pending"],
            meta["threshold"],
        )
        return SlideAlignmentResult(document=aligned_document, records=records, meta=meta)

    @staticmethod
    def _build_skip_result(
        content_document: ContentApprovalDocument,
        reason: str,
    ) -> SlideAlignmentResult:
        return SlideAlignmentResult(
            document=content_document,
            records=[],
            meta={
                "status": "skipped",
                "reason": reason,
            },
        )

    def _process_content_slide(
        self,
        *,
        slide: ContentSlide,
        card_map: dict[str, PrepareCard],
        candidate_slides: list[Slide],
        slide_assignments: dict[str, int],
        records: list[SlideAlignmentRecord],
    ) -> SlideAlignmentRecord:
        original_id = slide.id
        card = card_map.get(original_id)
        if card is None:
            logger.debug("SlideIdAligner: card_id=%s が prepare_document に見つかりません", original_id)
            return SlideAlignmentRecord(
                card_id=original_id,
                recommended_slide_id=None,
                confidence=0.0,
                reason="card_not_found",
                status="pending",
            )

        candidates = self._select_candidates(card, candidate_slides)
        match_request = self._build_match_request(card, candidates)
        response = self._client.match_slide(match_request)

        record = SlideAlignmentRecord(
            card_id=card.card_id,
            recommended_slide_id=response.slide_id,
            confidence=response.confidence,
            reason=response.reason,
            status="pending",
            candidates=tuple(candidate.id for candidate in candidates),
        )
        self._normalize_recommendation(record)
        self._handle_assignment(record, slide_assignments, records)
        return record

    @staticmethod
    def _normalize_recommendation(record: SlideAlignmentRecord) -> None:
        if record.recommended_slide_id and record.recommended_slide_id not in record.candidates:
            record.recommended_slide_id = None

    def _handle_assignment(
        self,
        record: SlideAlignmentRecord,
        slide_assignments: dict[str, int],
        records: list[SlideAlignmentRecord],
    ) -> None:
        recommended_slide_id = record.recommended_slide_id
        if not recommended_slide_id:
            return

        previous_index = slide_assignments.get(recommended_slide_id)
        if previous_index is None:
            record.status = "applied"
            if record.confidence < self._options.confidence_threshold:
                record.reason = self._append_reason(record.reason, "low_confidence")
            slide_assignments[recommended_slide_id] = len(records)
            return

        previous_record = records[previous_index]
        if record.confidence > previous_record.confidence:
            previous_record.recommended_slide_id = None
            previous_record.status = "pending"
            previous_record.reason = self._append_reason(previous_record.reason, "reassigned")
            record.status = "applied"
            if record.confidence < self._options.confidence_threshold:
                record.reason = self._append_reason(record.reason, "low_confidence")
            slide_assignments[recommended_slide_id] = len(records)
            return

        if previous_record.confidence < self._options.confidence_threshold:
            previous_record.reason = self._append_reason(previous_record.reason, "low_confidence")
        record.status = "pending"
        record.reason = self._append_reason(record.reason, "lower_than_existing")
        record.recommended_slide_id = None

    def _apply_fallback_assignments(
        self,
        records: list[SlideAlignmentRecord],
        slide_assignments: dict[str, int],
    ) -> int:
        assigned_slides = set(slide_assignments)
        fallback_applied = 0
        for index, record in enumerate(records):
            if record.status == "applied" and record.recommended_slide_id:
                continue
            if record.status == "pending" and record.recommended_slide_id:
                continue
            if not record.candidates:
                continue
            for candidate_id in record.candidates:
                if candidate_id not in assigned_slides:
                    record.recommended_slide_id = candidate_id
                    record.status = "fallback"
                    record.reason = self._append_reason(record.reason, "fallback_candidate")
                    assigned_slides.add(candidate_id)
                    slide_assignments[candidate_id] = index
                    fallback_applied += 1
                    break
        return fallback_applied

    def _build_aligned_slides(
        self,
        content_document: ContentApprovalDocument,
        records: list[SlideAlignmentRecord],
    ) -> tuple[list[ContentSlide], int]:
        record_map: dict[str, SlideAlignmentRecord] = {}
        for record in records:
            record_map.setdefault(record.card_id, record)

        updated_slides: list[ContentSlide] = []
        applied = 0
        for slide in content_document.slides:
            record = record_map.get(slide.id)
            if record and record.recommended_slide_id and record.status in {"applied", "fallback"}:
                updated_slides.append(slide.model_copy(update={"id": record.recommended_slide_id}))
                applied += 1
            else:
                updated_slides.append(slide)
        return updated_slides, applied

    @staticmethod
    def _collect_unmatched_spec_slides(
        relevant_spec_ids: set[str],
        slide_assignments: dict[str, int],
    ) -> list[str]:
        return [slide_id for slide_id in relevant_spec_ids if slide_id not in slide_assignments]

    @staticmethod
    def _build_unmatched_records(slide_ids: Iterable[str]) -> list[SlideAlignmentRecord]:
        return [
            SlideAlignmentRecord(
                card_id=slide_id,
                recommended_slide_id=None,
                confidence=0.0,
                reason="jobspec_unassigned",
                status="skipped",
            )
            for slide_id in slide_ids
        ]

    def _build_alignment_meta(
        self,
        *,
        content_document: ContentApprovalDocument,
        relevant_spec_ids: set[str],
        unmatched_spec_slides: list[str],
        applied: int,
        fallback: int,
        pending: int,
    ) -> dict[str, object]:
        return {
            "status": "completed",
            "threshold": self._options.confidence_threshold,
            "cards_total": len(content_document.slides),
            "jobspec_total": len(relevant_spec_ids),
            "jobspec_unassigned": len(unmatched_spec_slides),
            "applied": applied,
            "fallback": fallback,
            "pending": pending,
        }

    @staticmethod
    def _append_reason(origin: str | None, note: str) -> str:
        return note if not origin else f"{origin} | {note}"

    def _build_match_request(
        self,
        card: PrepareCard,
        candidates: list[Slide],
    ) -> SlideMatchRequest:
        summary_lines = [card.headline_or_title()]
        body_iter = card.iter_body_text()
        for _, text in zip(range(3), body_iter):
            summary_lines.append(text)
        summary_lines.extend(card.notes_text()[:3])
        card_summary = "\n".join(line.strip() for line in summary_lines if line.strip()) or card.headline_or_title()

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
            f"chapter: {card.resolved_chapter_title()}",
            f"story_phase: {card.role.story_phase or '未指定'}",
            f"intent_tags: {', '.join(card.resolved_intent_tags()) if card.resolved_intent_tags() else 'なし'}",
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
            card_chapter=card.resolved_chapter_title(),
            card_intent=tuple(card.resolved_intent_tags()),
            card_story_phase=card.role.story_phase,
            card_summary=card_summary,
            prompt=prompt,
            system_prompt=system_prompt,
            candidates=candidate_models,
        )

    def _select_candidates(self, card: PrepareCard, candidates: Iterable[Slide]) -> list[Slide]:
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
    def _heuristic_score(card: PrepareCard, slide: Slide) -> float:
        score = 0.0
        if slide.id == card.card_id:
            score += 5.0
        title = (slide.title or "").lower()
        chapter = card.resolved_chapter_title().lower()
        if chapter and chapter in title:
            score += 3.0
        phase = (card.role.story_phase or "").lower()
        if phase and phase in (slide.layout or "").lower():
            score += 1.5
        intent_tags = card.resolved_intent_tags()
        if intent_tags:
            for intent in intent_tags:
                if intent.lower() in title:
                    score += 1.0
        source_text = card.headline_or_title().lower()
        if slide.notes:
            ratio = SequenceMatcher(None, source_text, slide.notes.lower()).ratio()
            score += ratio * 2.0
        else:
            ratio = SequenceMatcher(None, source_text, title).ratio()
            score += ratio * 2.0
        return score
