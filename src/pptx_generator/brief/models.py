from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable, Literal

from pydantic import BaseModel, Field, field_validator

BriefActionType = Literal["approve", "return", "comment", "autofix", "regenerate"]


class BriefBodyBlock(BaseModel):
    """本文のブロック定義。"""

    type: str
    text: str | None = None
    headers: list[str] | None = None
    rows: list[list[str]] | None = None
    ref: str | None = None
    description: str | None = None
    data: dict[str, Any] | None = None

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class BriefNoteEntry(BaseModel):
    """ノート欄に出力する補足情報。"""

    type: str = "note"
    text: str

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("note text must not be empty")
        return stripped


class BriefCardContent(BaseModel):
    """カードの本文構造。"""

    title: str
    headline: str | None = None  # このページで最も伝えたい結論を短く明示する
    body: list[BriefBodyBlock] = Field(default_factory=list)
    notes: list[BriefNoteEntry] = Field(default_factory=list)


class BriefCardRole(BaseModel):
    """カードの役割情報。"""

    story_phase: Literal["introduction", "problem", "solution", "impact", "next"]
    intent_tags: list[str] = Field(default_factory=list)

    @field_validator("intent_tags", mode="before")
    @classmethod
    def normalize_intent_tags(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()]


class BriefCard(BaseModel):
    """テンプレート非依存のブリーフカード。"""

    card_id: str = Field(..., pattern=r"^[a-z0-9][a-z0-9\-]*$")
    order: int | None = None
    role: BriefCardRole
    content: BriefCardContent
    meta: dict[str, Any] = Field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Convenience helpers for downstream pipeline
    # ------------------------------------------------------------------ #
    def resolved_intent_tags(self) -> list[str]:
        intents = [tag for tag in self.role.intent_tags if tag]
        if not intents:
            intents = [self.role.story_phase]
        return intents

    def primary_intent(self) -> str:
        intents = self.resolved_intent_tags()
        return intents[0] if intents else self.role.story_phase

    def headline_or_title(self) -> str:
        return (self.content.headline or self.content.title).strip()

    def iter_body_text(self) -> Iterable[str]:
        for block in self.content.body:
            if block.text:
                text = block.text.strip()
                if text:
                    yield text
            if block.rows:
                for row in block.rows:
                    row_text = " | ".join(cell.strip() for cell in row if cell and cell.strip())
                    if row_text:
                        yield row_text
            if block.description:
                desc = block.description.strip()
                if desc:
                    yield desc

    def notes_text(self) -> list[str]:
        return [note.text.strip() for note in self.content.notes if note.text.strip()]

    def resolved_chapter_title(self) -> str:
        source_chapter = (self.meta.get("source_chapter") if isinstance(self.meta, dict) else None) or {}
        title = source_chapter.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()
        blueprint = (self.meta.get("blueprint") if isinstance(self.meta, dict) else None) or {}
        layout = blueprint.get("layout")
        if isinstance(layout, str) and layout.strip():
            return layout.strip()
        return self.content.title

    def blueprint_meta(self) -> dict[str, Any] | None:
        if isinstance(self.meta, dict):
            blueprint = self.meta.get("blueprint")
            if isinstance(blueprint, dict):
                return blueprint
        return None


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
    batch_card_ids: list[str] | None = None


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
    constraints: dict[str, Any] = Field(default_factory=dict)

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
        constraints: dict[str, Any] | None = None,
    ) -> "BriefGenerationMeta":
        normalized_source = json.dumps(source_payload, ensure_ascii=False, sort_keys=True)
        hash_value = hashlib.sha256(normalized_source.encode("utf-8")).hexdigest()
        stats = {
            "cards_total": len(document.cards),
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
            constraints=constraints or {},
        )
