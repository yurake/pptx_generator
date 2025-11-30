from __future__ import annotations

import hashlib
import json
import textwrap
from datetime import datetime, timezone
from typing import Any, Iterable, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

PrepareActionType = Literal["approve", "return", "comment", "autofix", "regenerate"]


class PrepareBodyBlock(BaseModel):
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


class PrepareNoteEntry(BaseModel):
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


class PrepareCardContent(BaseModel):
    """カードの本文構造。"""

    title: str | None = None
    headline: str | None = None  # このページで最も伝えたい結論を短く明示する
    subtitle: str | None = None
    body: list[PrepareBodyBlock] = Field(default_factory=list)
    notes: list[PrepareNoteEntry] = Field(default_factory=list)

    @field_validator("title", "headline", "subtitle", mode="before")
    @classmethod
    def normalize_heading(cls, value: Any) -> str | None:  # noqa: ANN401
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @model_validator(mode="after")
    def ensure_single_primary_heading(self) -> "PrepareCardContent":
        has_title = bool(self.title)
        has_headline = bool(self.headline)
        if has_title == has_headline:
            msg = "title と headline はどちらか一方のみ指定してください"
            raise ValueError(msg)
        return self


class PrepareCardRole(BaseModel):
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


class PrepareCard(BaseModel):
    """テンプレート非依存のプレペアカード。"""

    card_id: str = Field(..., pattern=r"^[a-z0-9][a-z0-9\-]*$")
    order: int | None = None
    role: PrepareCardRole
    content: PrepareCardContent
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
        value = self.content.headline or self.content.title
        return value.strip() if value else ""

    def subtitle_or_chapter(self) -> str | None:
        subtitle = self.content.subtitle
        if subtitle and subtitle.strip():
            return subtitle.strip()
        source_chapter = (self.meta.get("source_chapter") if isinstance(self.meta, dict) else None) or {}
        chapter_title = source_chapter.get("title")
        if isinstance(chapter_title, str) and chapter_title.strip():
            return chapter_title.strip()
        return None

    def iter_body_text(self) -> Iterable[str]:
        def _yield_segments(value: str) -> Iterable[str]:
            if "\n" in value:
                lines = value.splitlines()
            else:
                lines = [value]
            for line in lines:
                chunk = line.strip()
                if not chunk:
                    continue
                if len(chunk) <= 200:
                    yield chunk
                    continue
                for segment in textwrap.wrap(
                    chunk, width=200, drop_whitespace=True, break_long_words=True
                ):
                    segment_stripped = segment.strip()
                    if segment_stripped:
                        yield segment_stripped

        for block in self.content.body:
            if block.text:
                text = block.text.strip()
                if text:
                    for segment in _yield_segments(text):
                        yield segment
            if block.data:
                items = block.data.get("items")
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, str) and item.strip():
                            for segment in _yield_segments(item):
                                yield segment
                        elif isinstance(item, dict):
                            line = str(item.get("text") or "").strip()
                            if line:
                                level_raw = item.get("level", 0)
                                try:
                                    level = max(int(level_raw), 0)
                                except (TypeError, ValueError):
                                    level = 0
                                indent = "  " * level
                                for segment in _yield_segments(line):
                                    yield f"{indent}{segment}"
            if block.rows:
                for row in block.rows:
                    row_text = " | ".join(cell.strip() for cell in row if cell and cell.strip())
                    if row_text:
                        for segment in _yield_segments(row_text):
                            yield segment
            if block.description:
                desc = block.description.strip()
                if desc:
                    for segment in _yield_segments(desc):
                        yield segment

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
        return self.content.title or self.content.headline or ""

    def blueprint_meta(self) -> dict[str, Any] | None:
        if isinstance(self.meta, dict):
            blueprint = self.meta.get("blueprint")
            if isinstance(blueprint, dict):
                return blueprint
        return None


class PrepareChapterDefinition(BaseModel):
    """ストーリー章定義。"""

    id: str = Field(..., pattern=r"^[a-z0-9\-]+$")
    title: str
    description: str | None = None


class PrepareStoryContext(BaseModel):
    """プレペア全体の文脈情報。"""

    chapters: list[PrepareChapterDefinition] = Field(default_factory=list)
    tone: str | None = None
    must_have_messages: list[str] = Field(default_factory=list)


class PrepareDocument(BaseModel):
    """プレペアカード集合と文脈。"""

    prepare_id: str
    cards: list[PrepareCard] = Field(default_factory=list)
    story_context: PrepareStoryContext = Field(default_factory=PrepareStoryContext)
    meta: dict[str, Any] = Field(default_factory=dict)

    def compute_content_hash(self) -> str:
        """成果物全体のハッシュ値を返す。"""

        payload = self.model_dump(mode="json", exclude_none=True, exclude={"meta"})
        digest = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(digest.encode("utf-8")).hexdigest()


class PrepareLogEntry(BaseModel):
    """HITL アクションログ。"""

    card_id: str
    version: int
    action: PrepareActionType
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


class PrepareAIRecord(BaseModel):
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
    prompt_template_path: str | None = None
    prompt_template_instructions: str | None = None
    slide_input_path: str | None = None


class PrepareGenerationMeta(BaseModel):
    """生成メタデータ。"""

    prepare_id: str
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
    prompt_templates: list[dict[str, Any]] = Field(default_factory=list)
    slide_inputs: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def from_document(
        cls,
        *,
        document: PrepareDocument,
        policy_id: str,
        source_payload: dict[str, Any],
        cards_meta: list[dict[str, Any]],
        mode: Literal["dynamic", "static"] = "dynamic",
        blueprint_path: str | None = None,
        blueprint_hash: str | None = None,
        slot_summary: dict[str, int] | None = None,
        constraints: dict[str, Any] | None = None,
        prompt_templates: list[dict[str, Any]] | None = None,
        slide_inputs: list[dict[str, Any]] | None = None,
    ) -> "PrepareGenerationMeta":
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
            prepare_id=document.prepare_id,
            policy_id=policy_id,
            input_hash=hash_value,
            cards=cards_meta,
            statistics=stats,
            mode=mode,
            blueprint_path=blueprint_path,
            blueprint_hash=blueprint_hash,
            slot_coverage=slot_coverage,
            constraints=constraints or {},
            prompt_templates=prompt_templates or [],
            slide_inputs=slide_inputs or [],
        )
