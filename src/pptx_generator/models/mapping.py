"""マッピングステージ・GenerateReady 関連モデル。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from .common import TemplateStyle
from .content import JsonPatchOperation
from .jobs import JobAuth, JobMeta

__all__ = [
    "MappingSlideMeta",
    "GenerateReadySlide",
    "GenerateReadyMeta",
    "GenerateReadyDocument",
    "MappingCandidate",
    "MappingFallbackState",
    "MappingAIPatch",
    "MappingLogAnalyzerIssue",
    "MappingLogAnalyzerSummary",
    "MappingLogSlide",
    "MappingLogMeta",
    "MappingLog",
]


class MappingSlideMeta(BaseModel):
    section: str | None = None
    page_no: int | None = None
    sources: list[str] = Field(default_factory=list)
    fallback: str = "none"
    layout_mode: Literal["dynamic", "static"] | None = None
    blueprint_slide_id: str | None = None
    blueprint_slots: list[dict[str, Any]] | None = None
    auto_draw: list[dict[str, Any]] = Field(default_factory=list)
    layout_description: dict[str, Any] | None = None


class GenerateReadySlide(BaseModel):
    layout_id: str
    layout_name: str | None = None
    elements: dict[str, Any] = Field(default_factory=dict)
    meta: MappingSlideMeta


class GenerateReadyMeta(BaseModel):
    template_version: str | None = None
    template_path: str | None = None
    content_hash: str | None = None
    generated_at: str
    job_meta: JobMeta | None = None
    job_auth: JobAuth | None = None
    layout_mode: Literal["dynamic", "static"] = "dynamic"
    blueprint_path: str | None = None
    blueprint_hash: str | None = None
    slot_summary: dict[str, int] | None = None
    template_style: TemplateStyle | None = None


class GenerateReadyDocument(BaseModel):
    slides: list[GenerateReadySlide] = Field(default_factory=list)
    meta: GenerateReadyMeta

    @classmethod
    def parse_file(cls, path: str | Path) -> "GenerateReadyDocument":
        source = Path(path).read_text(encoding="utf-8")
        return cls.model_validate_json(source)


class MappingCandidate(BaseModel):
    layout_id: str
    score: float = Field(ge=0.0, le=1.0)


class MappingFallbackState(BaseModel):
    applied: bool = False
    history: list[str] = Field(default_factory=list)
    reason: str | None = None


class MappingAIPatch(BaseModel):
    patch_id: str
    description: str
    patch: list[JsonPatchOperation] = Field(default_factory=list)


class MappingLogAnalyzerIssue(BaseModel):
    issue_id: str
    issue_type: str
    severity: str
    message: str
    target: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    fix_type: str | None = None
    fix_payload: dict[str, Any] | None = None


class MappingLogAnalyzerSummary(BaseModel):
    issue_count: int = 0
    issue_counts_by_type: dict[str, int] = Field(default_factory=dict)
    issue_counts_by_severity: dict[str, int] = Field(default_factory=dict)
    issues: list[MappingLogAnalyzerIssue] = Field(default_factory=list)


class MappingLogSlide(BaseModel):
    ref_id: str
    selected_layout: str
    candidates: list[MappingCandidate] = Field(default_factory=list)
    fallback: MappingFallbackState = Field(default_factory=MappingFallbackState)
    ai_patch: list[MappingAIPatch] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    analyzer: MappingLogAnalyzerSummary = Field(default_factory=MappingLogAnalyzerSummary)
    layout_description: dict[str, Any] | None = None


class MappingLogMeta(BaseModel):
    mapping_time_ms: int | None = None
    fallback_count: int = 0
    ai_patch_count: int = 0
    analyzer_issue_count: int = 0
    analyzer_issue_counts_by_type: dict[str, int] = Field(default_factory=dict)
    analyzer_issue_counts_by_severity: dict[str, int] = Field(default_factory=dict)
    mode: Literal["dynamic", "static"] | None = None
    blueprint_path: str | None = None
    slot_summary: dict[str, int] | None = None
    static_slot_checks: dict[str, Any] | None = None


class MappingLog(BaseModel):
    slides: list[MappingLogSlide] = Field(default_factory=list)
    meta: MappingLogMeta = Field(default_factory=MappingLogMeta)
