"""LLM 応答の正規化と解析ヘルパー。"""

from __future__ import annotations

import json
import re
import textwrap
from typing import Iterable

from ..utils.text_lines import split_lines_preserve_blank

from .loggers import LLM_LOGGER
from .models import (
    AIGenerationRequest,
    AIGenerationResponse,
    SlideMatchRequest,
    SlideMatchResponse,
)

MAX_BODY_LINES = 6
MAX_BODY_LINE_LENGTH = 40


def _normalize_body(candidates: Iterable[str]) -> tuple[list[str], list[str]]:
    body_lines: list[str] = []
    warnings: list[str] = []
    wrapped = False
    truncated = False

    for candidate in candidates:
        text_raw = str(candidate)
        segments: list[str] = []
        for segment in split_lines_preserve_blank(text_raw):
            stripped = segment.strip()
            if stripped:
                segments.append(stripped)
            else:
                segments.append("")
        if segments:
            body_lines.extend(segments)
            continue
        stripped = text_raw.strip()
        if stripped:
            body_lines.append(stripped)

    if not body_lines:
        body_lines.append("自動生成コンテンツ")

    normalized: list[str] = []
    for line in body_lines:
        if len(normalized) >= MAX_BODY_LINES:
            truncated = True
            break
        stripped = line.strip()
        if not stripped:
            normalized.append("")
            continue
        if len(stripped) <= MAX_BODY_LINE_LENGTH:
            normalized.append(stripped)
            continue
        wrapped_segments = textwrap.wrap(
            stripped,
            width=MAX_BODY_LINE_LENGTH,
            drop_whitespace=True,
            break_long_words=True,
        )
        if wrapped_segments:
            wrapped = True
        for segment in wrapped_segments:
            if len(normalized) >= MAX_BODY_LINES:
                truncated = True
                break
            normalized.append(segment)
        if len(normalized) >= MAX_BODY_LINES:
            break

    if truncated:
        warnings.append("body_truncated")
    if wrapped and "body_truncated" not in warnings:
        warnings.append("body_wrapped")

    if not any(normalized):
        normalized.append("自動生成コンテンツ")

    return normalized, warnings


def _extract_json_from_text(text: str) -> dict[str, object]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _normalize_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    if confidence < 0.0:
        return 0.0
    if confidence > 1.0:
        return 1.0
    return confidence


def build_generation_response(
    text: str,
    request: AIGenerationRequest,
    *,
    model: str,
    finish_reason: str | None = None,
    refusal: str | None = None,
) -> AIGenerationResponse:
    LLM_LOGGER.info(
        "LLM response received",
        extra={
            "slide_id": request.slide.id,
            "model": model,
            "policy_id": request.policy.id,
            "intent": request.intent,
            "raw_response": text,
            "finish_reason": finish_reason or "",
            "refusal": refusal or "",
        },
    )
    warnings: list[str] = []
    if not text and refusal:
        warnings.append("response_refused")
        text = refusal
    elif not text and finish_reason and finish_reason != "stop":
        warnings.append(f"finish_{finish_reason}")

    if not text:
        return AIGenerationResponse(
            title=request.slide.title or request.prompt,
            body=[request.prompt],
            note=None,
            intent=request.intent,
            model=model,
            warnings=warnings,
            raw_text=text,
        )

    try:
        data = _extract_json_from_text(text)
    except json.JSONDecodeError:
        warnings.append("response_not_json")
        lines: list[str] = []
        for raw_line in split_lines_preserve_blank(text):
            if raw_line.strip():
                lines.append(raw_line.strip("-• "))
            else:
                lines.append("")
        title_index = next((i for i, line in enumerate(lines) if line.strip()), None)
        if title_index is None:
            title_source = request.slide.title or request.prompt
            body_candidates = []
        else:
            title_source = lines[title_index]
            body_candidates = lines[title_index + 1 :]
        body, body_warnings = _normalize_body(body_candidates)
        warnings.extend(body_warnings)
        title_text = str(title_source).strip() or request.slide.title or request.prompt
        return AIGenerationResponse(
            title=title_text,
            body=body,
            note=None,
            intent=request.intent,
            model=model,
            warnings=warnings,
            raw_text=text,
        )

    title_source = data.get("title") or request.slide.title or request.spec.meta.title
    body_candidates = data.get("body")
    if isinstance(body_candidates, list):
        body_raw = [str(item) for item in body_candidates]
    elif body_candidates is None:
        body_raw = []
    else:
        body_raw = [str(body_candidates)]
        warnings.append("body_not_array")

    body, body_warnings = _normalize_body(body_raw)
    warnings.extend(body_warnings)

    note_value = data.get("note")
    note = None if note_value in (None, "", "null") else str(note_value)

    intent_value = data.get("intent")
    intent = str(intent_value) if isinstance(intent_value, str) else request.intent

    title_text = str(title_source).strip() or request.slide.title or request.spec.meta.title
    return AIGenerationResponse(
        title=title_text,
        body=body,
        note=note,
        intent=intent,
        model=model,
        warnings=warnings,
        raw_text=text,
    )


def build_slide_match_response(
    text: str,
    request: SlideMatchRequest,
    *,
    model: str,
    finish_reason: str | None = None,
    refusal: str | None = None,
) -> SlideMatchResponse:
    LLM_LOGGER.info(
        "LLM slide match response",
        extra={
            "card_id": request.card_id,
            "model": model,
            "raw_response": text,
            "finish_reason": finish_reason or "",
            "refusal": refusal or "",
        },
    )
    warnings: list[str] = []
    if not text and refusal:
        warnings.append("response_refused")
        text = refusal
    elif not text and finish_reason and finish_reason != "stop":
        warnings.append(f"finish_{finish_reason}")

    if not text:
        return SlideMatchResponse(
            slide_id=None,
            confidence=0.0,
            reason=refusal,
            model=model,
            warnings=warnings,
            raw_text=text,
        )

    try:
        data = _extract_json_from_text(text)
    except json.JSONDecodeError:
        warnings.append("response_not_json")
        return SlideMatchResponse(
            slide_id=None,
            confidence=0.0,
            reason=text.strip() or refusal,
            model=model,
            warnings=warnings,
            raw_text=text,
        )

    slide_id_value = (
        data.get("slide_id")
        or data.get("recommended_slide_id")
        or data.get("slideId")
        or data.get("match")
    )
    slide_id = str(slide_id_value).strip() if slide_id_value else None
    reason_value = data.get("reason") or data.get("explanation")
    reason = str(reason_value).strip() if isinstance(reason_value, str) else None
    confidence = _normalize_confidence(data.get("confidence") or data.get("score"))

    candidate_ids = {candidate.slide_id for candidate in request.candidates}
    if slide_id and slide_id not in candidate_ids:
        warnings.append("unknown_slide_id")

    return SlideMatchResponse(
        slide_id=slide_id if slide_id in candidate_ids else None,
        confidence=confidence if slide_id in candidate_ids else 0.0,
        reason=reason,
        model=model,
        warnings=warnings,
        raw_text=text,
    )


__all__ = [
    "build_generation_response",
    "build_slide_match_response",
    "MAX_BODY_LINES",
    "MAX_BODY_LINE_LENGTH",
]
