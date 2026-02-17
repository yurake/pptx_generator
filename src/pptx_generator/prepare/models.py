from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field


class PrepareBodyBlock(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    text: str | None = None
    description: str | None = None
    data: dict[str, Any] | None = None
    headers: list[str] | None = None
    rows: list[list[Any]] | None = None


class PrepareCardContent(BaseModel):
    model_config = ConfigDict(extra="allow")

    headline: str | None = None
    title: str | None = None
    subtitle: str | None = None
    body: list[PrepareBodyBlock] = Field(default_factory=list)
    notes: list[Any] = Field(default_factory=list)


class PrepareCardRole(BaseModel):
    model_config = ConfigDict(extra="allow")

    story_phase: str | None = None
    intent_tags: list[str] = Field(default_factory=list)


class PrepareCard(BaseModel):
    model_config = ConfigDict(extra="allow")

    card_id: str
    order: int | None = None
    role: PrepareCardRole = Field(default_factory=PrepareCardRole)
    content: PrepareCardContent = Field(default_factory=PrepareCardContent)
    meta: dict[str, Any] = Field(default_factory=dict)

    def headline_or_title(self) -> str:
        for candidate in (
            self.content.headline,
            self.content.title,
            self.meta.get("headline"),
            self.meta.get("title"),
        ):
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return ""

    def subtitle_or_chapter(self) -> str | None:
        subtitle = self.content.subtitle
        if isinstance(subtitle, str) and subtitle.strip():
            return subtitle.strip()
        meta_value = self.meta.get("chapter") or self.meta.get("chapter_title")
        if isinstance(meta_value, str) and meta_value.strip():
            return meta_value.strip()
        return None

    def notes_text(self) -> list[str]:
        lines: list[str] = []
        for item in self.content.notes:
            if isinstance(item, PrepareBodyBlock):
                if item.text:
                    lines.append(item.text)
                if item.description:
                    lines.append(item.description)
                continue
            if isinstance(item, dict):
                text = item.get("text") or item.get("description")
                if isinstance(text, str) and text.strip():
                    lines.append(text.strip())
                continue
            if isinstance(item, str) and item.strip():
                lines.append(item.strip())
        return lines

    def primary_intent(self) -> str | None:
        return self.role.intent_tags[0] if self.role.intent_tags else None

    def resolved_intent_tags(self) -> list[str]:
        return [tag for tag in self.role.intent_tags if tag]

    def blueprint_meta(self) -> dict[str, Any] | None:
        meta = self.meta.get("blueprint")
        return meta if isinstance(meta, dict) else None

    def iter_body_text(self) -> Iterable[str]:
        for block in self.content.body:
            if block.type == "table":
                continue
            if block.type == "bullets":
                items = None
                if isinstance(block.data, dict):
                    items = block.data.get("items")
                if isinstance(items, list):
                    for entry in items:
                        if isinstance(entry, dict):
                            text = entry.get("text")
                            if isinstance(text, str) and text.strip():
                                yield text.strip()
                        elif isinstance(entry, str) and entry.strip():
                            yield entry.strip()
                continue
            if block.text and block.text.strip():
                yield block.text.strip()
            if block.description and block.description.strip():
                yield block.description.strip()


class PrepareChapterDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    title: str


class PrepareStoryContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    chapters: list[PrepareChapterDefinition] = Field(default_factory=list)
    tone: str | None = None
    must_have_messages: list[str] = Field(default_factory=list)


class PrepareDocument(BaseModel):
    model_config = ConfigDict(extra="allow")

    prepare_id: str
    cards: list[PrepareCard] = Field(default_factory=list)
    story_context: PrepareStoryContext = Field(default_factory=PrepareStoryContext)
    meta: dict[str, Any] = Field(default_factory=dict)

    def compute_content_hash(self) -> str:
        payload = self.model_dump(mode="json", exclude_none=True)
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


class PrepareGenerationMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    template_id: str | None = None
    template_source: str | None = None
    blueprint_path: str | None = None
    blueprint_hash: str | None = None


class PrepareLogEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    timestamp: str | None = None
    message: str | None = None
