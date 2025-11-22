"""Schematics for PrepareCard approval API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..prepare import (
    PrepareBodyBlock,
    PrepareCard,
    PrepareCardContent,
    PrepareCardRole,
    PrepareNoteEntry,
)

PrepareStatusType = Literal["draft", "approved", "returned"]


class PrepareCardCreatePayload(BaseModel):
    card: PrepareCard
    status: PrepareStatusType = "draft"
    autofix_applied: list[str] = Field(default_factory=list)


class CreatePrepareCardsRequest(BaseModel):
    spec_id: str = Field(..., min_length=1)
    cards: list[PrepareCardCreatePayload] = Field(default_factory=list)


class CreatePrepareCardsResponse(BaseModel):
    spec_id: str
    revision: str


class PrepareCardUpdate(BaseModel):
    role: PrepareCardRole | None = None
    content: PrepareCardContent | None = None
    meta: dict[str, Any] | None = None
    order: int | None = None
    intent_tags: list[str] | None = None
    headline: str | None = None
    notes: list[PrepareNoteEntry] | None = None
    body: list[PrepareBodyBlock] | None = None
    status: PrepareStatusType | None = None
    autofix_applied: list[str] | None = None


class PrepareCardUpdateResponse(BaseModel):
    revision: str
    content_hash: str


class PrepareCardApproveRequest(BaseModel):
    notes: str | None = None
    applied_autofix: list[str] | None = None


class PrepareCardApproveResponse(BaseModel):
    revision: str
    status: PrepareStatusType
    locked_at: datetime


class PrepareCardReturnRequest(BaseModel):
    reason: str
    requested_by: str | None = None


class PrepareCardReturnResponse(BaseModel):
    revision: str
    status: PrepareStatusType


class PrepareCardHistoryEntry(BaseModel):
    action: str
    actor: str | None = None
    timestamp: datetime
    notes: str | None = None
    applied_autofix: list[str] | None = None


class PrepareCardResponse(BaseModel):
    spec_id: str
    card: PrepareCard
    status: PrepareStatusType
    autofix_applied: list[str]
    revision: str
    history: list[PrepareCardHistoryEntry] = Field(default_factory=list)


class PrepareLogEntry(BaseModel):
    spec_id: str
    card_id: str
    action: str
    actor: str | None = None
    timestamp: datetime
    notes: str | None = None
    applied_autofix: list[str] | None = None


class PrepareLogsResponse(BaseModel):
    items: list[PrepareLogEntry] = Field(default_factory=list)
    next_offset: str | None = None


class ErrorDetail(BaseModel):
    field: str | None = None
    issue: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: list[ErrorDetail] | None = None

__all__ = [
    "PrepareStatusType",
    "PrepareCardCreatePayload",
    "CreatePrepareCardsRequest",
    "CreatePrepareCardsResponse",
    "PrepareCardUpdate",
    "PrepareCardUpdateResponse",
    "PrepareCardApproveRequest",
    "PrepareCardApproveResponse",
    "PrepareCardReturnRequest",
    "PrepareCardReturnResponse",
    "PrepareCardHistoryEntry",
    "PrepareCardResponse",
    "PrepareLogEntry",
    "PrepareLogsResponse",
]
