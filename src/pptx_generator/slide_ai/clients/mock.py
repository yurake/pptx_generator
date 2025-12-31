"""開発用モッククライアント。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Callable

from ..loggers import LLM_LOGGER
from ..models import (
    AIGenerationRequest,
    AIGenerationResponse,
    SlideMatchCandidate,
    SlideMatchRequest,
    SlideMatchResponse,
)
from ..response_parser import build_slide_match_response, _normalize_body


@dataclass
class HeuristicRule:
    matcher: Callable[[SlideMatchCandidate, SlideMatchRequest], float]
    weight: float = 1.0


class MockLLMClient:
    """開発用のモック LLM クライアント。"""

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        slide = request.slide
        title_source = slide.title or f"{request.spec.meta.title} ({slide.id})"
        title = str(title_source).strip() or request.prompt.strip() or f"{request.spec.meta.title} ({slide.id})"

        bullet_texts: list[str] = []
        for group in slide.iter_bullet_groups():
            for item in group.items:
                bullet_texts.append(item.text)

        if not bullet_texts:
            bullet_texts.append(request.prompt)

        if request.reference_text:
            reference_lines = [line.strip() for line in request.reference_text.splitlines() if line.strip()]
            bullet_texts.extend(reference_lines)

        body, warnings = _normalize_body(bullet_texts)
        note = f"{request.policy.name} ポリシーを使用して自動生成しました。" if request.policy.name else None

        raw_payload = {
            "title": title,
            "body": body,
            "note": note,
            "intent": request.intent,
        }
        LLM_LOGGER.info(
            "mock response",
            extra={"slide_id": slide.id, "intent": request.intent, "model": request.policy.model},
        )
        return AIGenerationResponse(
            title=title,
            body=body,
            note=note,
            intent=request.intent,
            model=request.policy.model,
            warnings=warnings,
            raw_text=json.dumps(raw_payload, ensure_ascii=False),
        )

    def match_slide(self, request: SlideMatchRequest) -> SlideMatchResponse:
        if not request.candidates:
            return SlideMatchResponse(
                slide_id=None,
                confidence=0.0,
                reason="no candidates",
                model="mock-local",
            )

        rules: list[HeuristicRule] = [
            HeuristicRule(_score_card_id, weight=5.0),
            HeuristicRule(_score_chapter, weight=3.0),
            HeuristicRule(_score_title_similarity, weight=2.0),
            HeuristicRule(_score_story_phase, weight=1.0),
            HeuristicRule(_score_intent, weight=1.0),
        ]

        scored = []
        for candidate in request.candidates:
            score = 0.0
            for rule in rules:
                score += rule.matcher(candidate, request) * rule.weight
            scored.append((score, candidate))

        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best_candidate = scored[0]
        if best_score <= 0:
            return SlideMatchResponse(
                slide_id=None,
                confidence=0.0,
                reason="heuristic match not found",
                model="mock-local",
            )
        confidence = min(1.0, best_score / 5.0)
        return build_slide_match_response(
            json.dumps({"slide_id": best_candidate.slide_id, "confidence": confidence}),
            request,
            model="mock-local",
        )


def _score_card_id(candidate: SlideMatchCandidate, request: SlideMatchRequest) -> float:
    return 1.0 if candidate.slide_id == request.card_id else 0.0


def _score_chapter(candidate: SlideMatchCandidate, request: SlideMatchRequest) -> float:
    title = (candidate.title or "").lower()
    chapter = (request.card_chapter or "").lower()
    return 1.0 if chapter and chapter in title else 0.0


def _score_title_similarity(candidate: SlideMatchCandidate, request: SlideMatchRequest) -> float:
    title = (candidate.title or "").lower()
    summary = request.card_summary.lower()
    if not title or not summary:
        return 0.0
    ratio = SequenceMatcher(None, title, summary[: len(title)]).ratio()
    return ratio


def _score_story_phase(candidate: SlideMatchCandidate, request: SlideMatchRequest) -> float:
    phase = request.card_story_phase
    if not phase:
        return 0.0
    layout = (candidate.layout or "").lower()
    phase_lower = phase.lower()
    if phase_lower in layout or layout.startswith(phase_lower[:3]):
        return 1.0
    return 0.0


def _score_intent(candidate: SlideMatchCandidate, request: SlideMatchRequest) -> float:
    intents = request.card_intent
    if not intents:
        return 0.0
    title = (candidate.title or "").lower()
    return 1.0 if any(intent and intent.lower() in title for intent in intents) else 0.0


__all__ = ["MockLLMClient"]
