from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

BriefEvidenceType = Literal["url", "source_id", "note"]
BriefStatusType = Literal["draft", "approved", "returned"]
BriefActionType = Literal["approve", "return", "comment", "autofix", "regenerate"]


class BriefEvidence(BaseModel):
    """支援情報の出典を表す。"""

    type: BriefEvidenceType
    value: str

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: str, info) -> str:
        if value.strip():
            return value
        raise ValueError("evidence value must not be empty")


class BriefSupportingPoint(BaseModel):
    """支援ポイントと出典情報。"""

    statement: str = Field(..., max_length=280)
    evidence: BriefEvidence | None = None


class BriefStoryInfo(BaseModel):
    """ストーリー軸情報。"""

    phase: Literal["introduction", "problem", "solution", "impact", "next"]
    goal: str | None = None
    tension: str | None = None
    resolution: str | None = None


class BriefCardMeta(BaseModel):
    """カードのメタデータ。"""

    owner: str | None = None
    updated_at: datetime | None = None

    @field_validator("updated_at", mode="before")
    @classmethod
    def normalize_updated_at(cls, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))


class BriefCard(BaseModel):
    """テンプレート非依存のブリーフカード。"""

    card_id: str = Field(..., pattern=r"^[a-z0-9\-]+$")
    chapter: str
    message: str = Field(..., min_length=1, max_length=200)
    narrative: list[str] = Field(default_factory=list)
    supporting_points: list[BriefSupportingPoint] = Field(default_factory=list)
    story: BriefStoryInfo
    intent_tags: list[str] = Field(default_factory=list)
    status: BriefStatusType = "draft"
    autofix_applied: list[str] = Field(default_factory=list)
    meta: BriefCardMeta | None = None
    layout_mode: Literal["dynamic", "static"] = "dynamic"
    slide_id: str | None = None
    slot_id: str | None = Field(None, pattern=r"^[a-z0-9_\-\.]+$")
    required: bool | None = None
    slot_fulfilled: bool | None = None
    blueprint_slot: dict[str, Any] | None = None

    @field_validator("intent_tags", mode="before")
    @classmethod
    def normalize_intent_tags(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()]


class BriefChapterDefinition(BaseModel):
    """ストーリー章定義。"""

    id: str = Field(..., pattern=r"^[a-z0-9\-]+$")
    title: str
    description: str | None = None


class BriefStoryContext(BaseModel):
    """ブリーフ全体の文脈情報。"""

    chapters: list[BriefChapterDefinition] = Field(default_factory=list)
    tone: str | None = None
    must_have_messages: list[str] = Field(default_factory=list)


class BriefDocument(BaseModel):
    """ブリーフカード集合と文脈。"""

    brief_id: str
    cards: list[BriefCard] = Field(default_factory=list)
    story_context: BriefStoryContext = Field(default_factory=BriefStoryContext)

    def compute_content_hash(self) -> str:
        """成果物全体のハッシュ値を返す。"""

        payload = self.model_dump(mode="json", exclude_none=True)
        digest = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(digest.encode("utf-8")).hexdigest()

    def ensure_all_status(self, status: BriefStatusType) -> None:
        """全カードが指定ステータスであることを検証する。"""

        invalid = [card.card_id for card in self.cards if card.status != status]
        if invalid:
            joined = ", ".join(invalid)
            raise ValueError(f"カードのステータスが一致しません: {joined}")


class BriefLogEntry(BaseModel):
    """HITL アクションログ。"""

    card_id: str
    version: int
    action: BriefActionType
    actor: str | None = None
    timestamp: datetime
    notes: str | None = None
    applied_autofix: list[str] = Field(default_factory=list)
    diff_snapshot: dict[str, Any] | None = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def normalize_timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))


class BriefAIRecord(BaseModel):
    """生成 AI 呼び出しログ。"""

    card_id: str
    prompt_template: str
    model: str = "mock-local"
    prompt_fragment: str | None = None
    response_digest: str | None = None
    warnings: list[str] = Field(default_factory=list)
    tokens: dict[str, int] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BriefGenerationMeta(BaseModel):
    """生成メタデータ。"""

    brief_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    policy_id: str
    input_hash: str
    cards: list[dict[str, Any]] = Field(default_factory=list)
    statistics: dict[str, int] = Field(default_factory=dict)
    mode: Literal["dynamic", "static"] = "dynamic"
    blueprint_path: str | None = None
    blueprint_hash: str | None = None
    slot_coverage: dict[str, int] = Field(default_factory=dict)

    @classmethod
    def from_document(
        cls,
        *,
        document: BriefDocument,
        policy_id: str,
        source_payload: dict[str, Any],
        cards_meta: list[dict[str, Any]],
        mode: Literal["dynamic", "static"] = "dynamic",
        blueprint_path: str | None = None,
        blueprint_hash: str | None = None,
        slot_summary: dict[str, int] | None = None,
    ) -> "BriefGenerationMeta":
        normalized_source = json.dumps(source_payload, ensure_ascii=False, sort_keys=True)
        hash_value = hashlib.sha256(normalized_source.encode("utf-8")).hexdigest()
        stats = {
            "cards_total": len(document.cards),
            "approved": sum(1 for card in document.cards if card.status == "approved"),
            "returned": sum(1 for card in document.cards if card.status == "returned"),
        }
        slot_coverage = slot_summary or {}
        if slot_summary:
            stats.update(
                {
                    "required_slot_total": slot_summary.get("required_total", 0),
                    "required_slot_fulfilled": slot_summary.get("required_fulfilled", 0),
                    "optional_slot_total": slot_summary.get("optional_total", 0),
                    "optional_slot_used": slot_summary.get("optional_used", 0),
                }
            )
        return cls(
            brief_id=document.brief_id,
            policy_id=policy_id,
            input_hash=hash_value,
            cards=cards_meta,
            statistics=stats,
            mode=mode,
            blueprint_path=blueprint_path,
            blueprint_hash=blueprint_hash,
            slot_coverage=slot_coverage,
        )
