"""Pydantic models for the content approval API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, RootModel, field_validator

from ..models import ContentTableData


class StoryMetadata(BaseModel):
    """ストーリー関連メタ情報。"""

    phase: str
    chapter_id: str | None = None
    angle: str | None = None


class TableDataPayload(BaseModel):
    """テーブルデータのペイロード。"""

    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)

    def to_content_table(self) -> ContentTableData:
        return ContentTableData(headers=self.headers, rows=self.rows)


class CardPayload(BaseModel):
    """カードの共通フィールド。"""

    title: str
    body: list[str] = Field(default_factory=list)
    table_data: TableDataPayload | None = None
    note: str | None = None
    intent: str | None = None
    type_hint: str | None = None
    story: StoryMetadata | None = None


class CardCreate(CardPayload):
    """カード作成ペイロード。"""

    slide_id: str


class CreateCardsRequest(BaseModel):
    """カード一括作成リクエスト。"""

    spec_id: str = Field(..., min_length=1)
    cards: list[CardCreate] = Field(default_factory=list)

    @field_validator("cards")
    @classmethod
    def ensure_cards_not_empty(cls, value: list[CardCreate]) -> list[CardCreate]:
        if not value:
            msg = "cards には 1 件以上のカードを指定してください"
            raise ValueError(msg)
        return value


class CreateCardsResponse(BaseModel):
    """カード作成レスポンス。"""

    spec_id: str
    revision: str


class CardUpdate(CardPayload):
    """カード更新リクエスト。"""

    autofix_applied: list[str] | None = None


class CardUpdateResponse(BaseModel):
    """カード更新レスポンス。"""

    revision: str
    content_hash: str


class CardApproveRequest(BaseModel):
    """承認リクエスト。"""

    notes: str | None = None
    applied_autofix: list[str] | None = None


class CardApproveResponse(BaseModel):
    """承認レスポンス。"""

    revision: str
    status: str
    locked_at: datetime


class CardReturnRequest(BaseModel):
    """差戻しリクエスト。"""

    reason: str
    requested_by: str | None = None


class CardReturnResponse(BaseModel):
    """差戻しレスポンス。"""

    revision: str
    status: str


class CardHistoryEntry(BaseModel):
    """カード履歴エントリ。"""

    action: str
    actor: str | None = None
    timestamp: datetime
    notes: str | None = None
    applied_autofix: list[str] | None = None
    ai_grade: str | None = None


class CardResponse(BaseModel):
    """カード取得レスポンス。"""

    spec_id: str
    slide_id: str
    title: str
    body: list[str]
    table_data: TableDataPayload | None = None
    note: str | None = None
    intent: str | None = None
    type_hint: str | None = None
    story: StoryMetadata | None = None
    status: str
    revision: str
    history: list[CardHistoryEntry] = Field(default_factory=list)


class LogEntry(BaseModel):
    """監査ログの単一エントリ。"""

    spec_id: str
    slide_id: str
    action: str
    actor: str | None = None
    timestamp: datetime
    notes: str | None = None
    applied_autofix: list[str] | None = None
    ai_grade: str | None = None


class LogsResponse(BaseModel):
    """監査ログレスポンス。"""

    items: list[LogEntry] = Field(default_factory=list)
    next_offset: str | None = None


class ErrorDetail(BaseModel):
    """エラー詳細。"""

    field: str | None = None
    issue: str


class ErrorResponse(BaseModel):
    """API エラーレスポンス。"""

    error: str
    message: str
    details: list[ErrorDetail] | None = None


class RawJSON(RootModel[Any]):
    """任意の JSON を返したい場合のラッパー。"""

    root: Any
