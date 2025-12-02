"""コンテンツ承認・レビュー関連モデル。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

__all__ = [
    "ContentTableData",
    "ContentElements",
    "JsonPatchOp",
    "JsonPatchOperation",
    "AutoFixProposal",
    "AIReviewIssue",
    "AIReviewResult",
    "ContentSlideSource",
    "ContentSlide",
    "ContentDocumentMeta",
    "ContentApprovalDocument",
    "ContentReviewLogEntry",
    "ContentSlideStatus",
]

ContentSlideStatus = Literal["draft", "approved", "returned"]
JsonPatchOp = Literal["add", "remove", "replace", "move", "copy", "test"]


class ContentTableData(BaseModel):
    """テーブルデータ。"""

    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)

    @field_validator("rows", mode="before")
    @classmethod
    def normalize_rows(cls, value: list[list[str | int | float]]) -> list[list[str]]:
        return [[str(cell) for cell in row] for row in value]

    @field_validator("rows")
    @classmethod
    def validate_row_length(
        cls,
        value: list[list[str]],
        info: ValidationInfo,
    ) -> list[list[str]]:
        headers: list[str] = info.data.get("headers", [])
        if headers:
            expected = len(headers)
            for row in value:
                if len(row) != expected:
                    raise ValueError("各行の列数は headers と一致する必要があります")
        return value


class ContentElements(BaseModel):
    """カード要素。"""

    title: str
    subtitle: str | None = None
    body: list[str] = Field(default_factory=list)
    table_data: ContentTableData | None = None
    note: str | None = None

    @field_validator("subtitle", mode="before")
    @classmethod
    def normalize_optional_subtitle(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("body", mode="before")
    @classmethod
    def normalize_body(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]


class JsonPatchOperation(BaseModel):
    """JSON Patch 操作。"""

    op: JsonPatchOp
    path: str
    value: object | None = None
    from_path: str | None = Field(default=None, alias="from")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("path")
    @classmethod
    def ensure_absolute_path(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("JSON Patch path は '/' で開始する必要があります")
        return value

    @field_validator("from_path")
    @classmethod
    def ensure_from_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.startswith("/"):
            raise ValueError("JSON Patch from は '/' で開始する必要があります")
        return value


class AutoFixProposal(BaseModel):
    """AI が提示する修正提案。"""

    patch_id: str
    description: str
    patch: list[JsonPatchOperation] = Field(default_factory=list)

    @field_validator("patch", mode="before")
    @classmethod
    def normalize_patch(
        cls,
        value: list[JsonPatchOperation] | JsonPatchOperation | None,
    ) -> list[JsonPatchOperation]:
        if value is None:
            return []
        if isinstance(value, JsonPatchOperation):
            return [value]
        return value

    @field_validator("patch")
    @classmethod
    def ensure_non_empty(cls, value: list[JsonPatchOperation]) -> list[JsonPatchOperation]:
        if not value:
            raise ValueError("Auto-fix 提案には少なくとも 1 件の JSON Patch を含めてください")
        return value


class AIReviewIssue(BaseModel):
    """AI レビューの指摘。"""

    code: str
    message: str
    severity: Literal["info", "warning", "critical"] | None = None


class AIReviewResult(BaseModel):
    """AI レビューの結果。"""

    grade: Literal["A", "B", "C"]
    issues: list[AIReviewIssue] = Field(default_factory=list)
    autofix_proposals: list[AutoFixProposal] = Field(default_factory=list)


class ContentSlideSource(BaseModel):
    """カード生成元メタ情報。"""

    card_id: str | None = None
    order: int | None = None
    story_phase: str | None = None
    intent_tags: tuple[str, ...] = ()
    blueprint: dict[str, Any] | None = None

    @field_validator("intent_tags", mode="before")
    @classmethod
    def _normalize_intent_tags(cls, value: object) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, (list, tuple, set)):
            items = [str(item).strip() for item in value if str(item).strip()]
        else:
            text = str(value).strip()
            items = [text] if text else []
        seen: set[str] = set()
        unique: list[str] = []
        for item in items:
            lower = item.lower()
            if lower in seen:
                continue
            seen.add(lower)
            unique.append(item)
        return tuple(unique)


class ContentSlide(BaseModel):
    """承認ドキュメントのカード。"""

    id: str
    intent: str
    type_hint: str | None = None
    elements: ContentElements
    status: ContentSlideStatus = "draft"
    ai_review: AIReviewResult | None = None
    applied_autofix: list[str] = Field(default_factory=list)
    source: ContentSlideSource | None = None

    @field_validator("applied_autofix", mode="before")
    @classmethod
    def normalize_autofix_ids(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return value


class ContentDocumentMeta(BaseModel):
    """承認ドキュメントメタ情報。"""

    tone: str | None = None
    audience: str | None = None
    summary: str | None = None


class ContentApprovalDocument(BaseModel):
    """承認済みドキュメント。"""

    slides: list[ContentSlide] = Field(default_factory=list)
    meta: ContentDocumentMeta | None = None

    def ensure_all_approved(self) -> None:
        not_approved = [slide.id for slide in self.slides if slide.status != "approved"]
        if not_approved:
            msg = "承認済みドキュメント内に未承認のカードがあります: " + ", ".join(not_approved)
            raise ValueError(msg)


class ContentReviewLogEntry(BaseModel):
    """承認ログ。"""

    slide_id: str
    action: Literal["approve", "return", "comment", "autofix"]
    actor: str
    timestamp: datetime
    notes: str | None = None
    ai_grade: Literal["A", "B", "C"] | None = None
    applied_autofix: list[str] = Field(default_factory=list)

    @field_validator("applied_autofix", mode="before")
    @classmethod
    def normalize_autofix(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        return value
