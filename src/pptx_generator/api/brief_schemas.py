"""Schematics for BriefCard approval API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..brief import (
    BriefBodyBlock,
    BriefCard,
    BriefCardContent,
    BriefCardRole,
    BriefNoteEntry,
)

BriefStatusType = Literal["draft", "approved", "returned"]


class BriefCardCreatePayload(BaseModel):
    card: BriefCard
    status: BriefStatusType = "draft"
    autofix_applied: list[str] = Field(default_factory=list)


class CreateBriefCardsRequest(BaseModel):
    spec_id: str = Field(..., min_length=1)
    cards: list[BriefCardCreatePayload] = Field(default_factory=list)


class CreateBriefCardsResponse(BaseModel):
    spec_id: str
    revision: str


class BriefCardUpdate(BaseModel):
    role: BriefCardRole | None = None
    content: BriefCardContent | None = None
    meta: dict[str, Any] | None = None
    order: int | None = None
    intent_tags: list[str] | None = None
    headline: str | None = None
    notes: list[BriefNoteEntry] | None = None
    body: list[BriefBodyBlock] | None = None
    status: BriefStatusType | None = None
    autofix_applied: list[str] | None = None


class BriefCardUpdateResponse(BaseModel):
    revision: str
    content_hash: str


class BriefCardApproveRequest(BaseModel):
    notes: str | None = None
    applied_autofix: list[str] | None = None


class BriefCardApproveResponse(BaseModel):
    revision: str
    status: BriefStatusType
    locked_at: datetime


class BriefCardReturnRequest(BaseModel):
    reason: str
    requested_by: str | None = None


class BriefCardReturnResponse(BaseModel):
    revision: str
    status: BriefStatusType


class BriefCardHistoryEntry(BaseModel):
    action: str
    actor: str | None = None
    timestamp: datetime
    notes: str | None = None
    applied_autofix: list[str] | None = None


class BriefCardResponse(BaseModel):
    spec_id: str
    card: BriefCard
    status: BriefStatusType
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
