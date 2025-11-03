"""Pydantic models for the brief approval API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


BriefEvidenceType = Literal["url", "source_id", "note"]


class BriefStoryPayload(BaseModel):
    phase: str
    goal: str | None = None
    tension: str | None = None
    resolution: str | None = None


class BriefSupportingPointPayload(BaseModel):
    statement: str
    evidence_type: BriefEvidenceType | None = None
    evidence_value: str | None = None

    @field_validator("statement")
    @classmethod
    def ensure_statement(cls, value: str) -> str:
        if not value.strip():
            msg = "supporting_points[].statement は空白のみではいけません"
            raise ValueError(msg)
        return value


class BriefCardPayload(BaseModel):
    chapter: str
    message: str
    narrative: list[str] = Field(default_factory=list)
    supporting_points: list[BriefSupportingPointPayload] = Field(default_factory=list)
    story: BriefStoryPayload
    intent_tags: list[str] = Field(default_factory=list)
    autofix_applied: list[str] = Field(default_factory=list)


class BriefCardCreate(BriefCardPayload):
    card_id: str


class CreateBriefCardsRequest(BaseModel):
    spec_id: str = Field(..., min_length=1)
    cards: list[BriefCardCreate] = Field(default_factory=list)

    @field_validator("cards")
    @classmethod
    def ensure_cards_not_empty(cls, cards: list[BriefCardCreate]) -> list[BriefCardCreate]:
        if not cards:
            msg = "cards には 1 件以上のカードを指定してください"
            raise ValueError(msg)
        return cards


class CreateBriefCardsResponse(BaseModel):
    spec_id: str
    revision: str


class BriefCardUpdate(BaseModel):
    chapter: str | None = None
    message: str | None = None
    narrative: list[str] | None = None
    supporting_points: list[BriefSupportingPointPayload] | None = None
    story: BriefStoryPayload | None = None
    intent_tags: list[str] | None = None
    autofix_applied: list[str] | None = None


class BriefCardUpdateResponse(BaseModel):
    revision: str
    content_hash: str


class BriefCardApproveRequest(BaseModel):
    notes: str | None = None
    applied_autofix: list[str] | None = None


class BriefCardApproveResponse(BaseModel):
    revision: str
    status: str
    locked_at: datetime


class BriefCardReturnRequest(BaseModel):
    reason: str
    requested_by: str | None = None


class BriefCardReturnResponse(BaseModel):
    revision: str
    status: str


class BriefCardHistoryEntry(BaseModel):
    action: str
    actor: str | None = None
    timestamp: datetime
    notes: str | None = None
    applied_autofix: list[str] | None = None


class BriefCardResponse(BaseModel):
    spec_id: str
    card_id: str
    chapter: str
    message: str
    narrative: list[str]
    supporting_points: list[BriefSupportingPointPayload]
    story: BriefStoryPayload
    intent_tags: list[str]
    status: str
    autofix_applied: list[str]
    revision: str
    history: list[BriefCardHistoryEntry] = Field(default_factory=list)


class BriefLogEntry(BaseModel):
    spec_id: str
    card_id: str
    action: str
    actor: str | None = None
    timestamp: datetime
    notes: str | None = None
    applied_autofix: list[str] | None = None


class BriefLogsResponse(BaseModel):
    items: list[BriefLogEntry] = Field(default_factory=list)
    next_offset: str | None = None


class ErrorDetail(BaseModel):
    field: str | None = None
    issue: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: list[ErrorDetail] | None = None
