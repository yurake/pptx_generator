"""Draft API 用 Pydantic スキーマ。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..models import DraftDocument, DraftLogEntry


class DraftBoardResponse(BaseModel):
    """ボード取得レスポンス。"""

    spec_id: str
    revision: str
    board: DraftDocument


class LayoutHintUpdateRequest(BaseModel):
    """layout_hint 更新リクエスト。"""

    layout_hint: str
    notes: str | None = None


class MoveSlideRequest(BaseModel):
    """スライド移動リクエスト。"""

    target_section: str = Field(..., min_length=1)
    position: int | None = Field(default=None, ge=1)


class SectionApproveRequest(BaseModel):
    """セクション承認リクエスト。"""

    notes: str | None = None


class AppendixUpdateRequest(BaseModel):
    """付録フラグ更新リクエスト。"""

    appendix: bool
    notes: str | None = None


class DraftLogEntriesResponse(BaseModel):
    """ログ一覧レスポンス。"""

    items: list[DraftLogEntry] = Field(default_factory=list)
    next_offset: int | None = None


class RevisionResponse(BaseModel):
    """リビジョンのみを返すレスポンス。"""

    revision: str
