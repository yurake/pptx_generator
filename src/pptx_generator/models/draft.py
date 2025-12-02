"""ドラフト構造モデル。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

__all__ = [
    "DraftStatus",
    "DraftLayoutCandidate",
    "DraftLayoutScoreDetail",
    "DraftAnalyzerSummary",
    "DraftSlideCard",
    "DraftSection",
    "DraftTemplateMismatch",
    "DraftMeta",
    "DraftDocument",
    "DraftLogEntry",
]

DraftStatus = Literal["draft", "approved", "returned"]


class DraftLayoutCandidate(BaseModel):
    layout_id: str
    score: float = Field(ge=0.0, le=1.0)


class DraftLayoutScoreDetail(BaseModel):
    uses_tag: float = 0.0
    content_capacity: float = 0.0
    diversity: float = 0.0
    analyzer_support: float = 0.0
    ai_recommendation: float = 0.0

    @property
    def total(self) -> float:
        return round(
            self.uses_tag
            + self.content_capacity
            + self.diversity
            + self.analyzer_support
            + self.ai_recommendation,
            3,
        )


class DraftAnalyzerSummary(BaseModel):
    severity_high: int = 0
    severity_medium: int = 0
    severity_low: int = 0
    layout_consistency: Literal["ok", "warn", "error"] | None = None
    blocking_tags: tuple[str, ...] = ()


class DraftSlideCard(BaseModel):
    ref_id: str
    order: int
    layout_hint: str
    locked: bool = False
    status: DraftStatus = "draft"
    layout_candidates: list[DraftLayoutCandidate] = Field(default_factory=list)
    appendix: bool = False
    layout_score_detail: DraftLayoutScoreDetail | None = None
    analyzer_summary: DraftAnalyzerSummary | None = None


class DraftSection(BaseModel):
    name: str
    order: int
    status: DraftStatus = "draft"
    slides: list[DraftSlideCard] = Field(default_factory=list)
    chapter_template_id: str | None = None
    template_match_score: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("slides")
    @classmethod
    def ensure_unique_slide_refs(cls, value: list[DraftSlideCard]) -> list[DraftSlideCard]:
        ref_ids = {card.ref_id for card in value}
        if len(ref_ids) != len(value):
            raise ValueError("セクション内の ref_id は一意である必要があります")
        return value


class DraftTemplateMismatch(BaseModel):
    section_id: str
    issue: Literal["missing", "excess", "insufficient", "capacity"]
    severity: Literal["warn", "blocker"] = "warn"
    detail: str | None = None


class DraftMeta(BaseModel):
    target_length: int | None = None
    structure_pattern: str | None = None
    appendix_limit: int | None = None
    template_id: str | None = None
    template_match_score: float | None = Field(default=None, ge=0.0, le=1.0)
    template_mismatch: list[DraftTemplateMismatch] = Field(default_factory=list)
    return_reason_stats: dict[str, int] = Field(default_factory=dict)
    analyzer_summary: dict[str, int] = Field(default_factory=dict)


class DraftDocument(BaseModel):
    sections: list[DraftSection] = Field(default_factory=list)
    meta: DraftMeta = Field(default_factory=DraftMeta)

    @field_validator("sections")
    @classmethod
    def ensure_section_order(cls, value: list[DraftSection]) -> list[DraftSection]:
        orders = {section.order for section in value}
        if len(orders) != len(value):
            raise ValueError("セクション order が重複しています")
        return value


class DraftLogEntry(BaseModel):
    target_type: Literal["section", "slide"]
    target_id: str
    action: Literal["generate", "move", "hint", "approve", "appendix", "return"]
    actor: str | None = None
    timestamp: datetime
    notes: str | None = None
    changes: dict[str, object] | None = None
