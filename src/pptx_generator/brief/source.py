from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .models import BriefEvidence, BriefEvidenceType, BriefSupportingPoint


class BriefSourceMeta(BaseModel):
    """ブリーフ入力のメタ情報。"""

    title: str
    brief_id: str | None = None
    client: str | None = None
    objective: str | None = None
    locale: str | None = "ja-JP"


class BriefSourceSupportingPoint(BaseModel):
    """入力定義の支援ポイント。"""

    statement: str
    evidence_type: BriefEvidenceType | None = None
    evidence_value: str | None = None

    def to_brief_supporting_point(self) -> BriefSupportingPoint:
        evidence: BriefEvidence | None = None
        if self.evidence_type and self.evidence_value:
            evidence = BriefEvidence(type=self.evidence_type, value=self.evidence_value)
        return BriefSupportingPoint(statement=self.statement, evidence=evidence)


class BriefSourceChapter(BaseModel):
    """入力定義の章情報。"""

    id: str = Field(..., pattern=r"^[a-z0-9\\-]+$")
    title: str
    message: str | None = None
    details: list[str] = Field(default_factory=list)
    supporting_points: list[BriefSourceSupportingPoint] = Field(default_factory=list)
    story_hint: str | None = None
    intent_tags: list[str] = Field(default_factory=list)

    @field_validator("intent_tags", mode="before")
    @classmethod
    def normalize_intents(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()]


class BriefSourceDocument(BaseModel):
    """ブリーフ入力ドキュメント。"""

    meta: BriefSourceMeta
    chapters: list[BriefSourceChapter] = Field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "BriefSourceDocument":
        return cls.model_validate(payload)

    @classmethod
    def parse_file(cls, path: str | Path) -> "BriefSourceDocument":
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() in {".json", ".jsonc"}:
            payload = json.loads(text)
            return cls.from_payload(payload)
        return cls._from_markdown(text, brief_id=path.stem)

    @classmethod
    def _from_markdown(cls, text: str, *, brief_id: str | None = None) -> "BriefSourceDocument":
        lines = text.splitlines()
        title: str | None = None
        intro_lines: list[str] = []
        chapters: list[BriefSourceChapter] = []

        current_title: str | None = None
        current_narrative: list[str] = []
        current_supporting: list[str] = []

        def finalize_current() -> None:
            nonlocal current_title, current_narrative, current_supporting
            if not current_title:
                return
            chapter_id = re.sub(r"[^a-z0-9]+", "-", current_title.lower()).strip("-") or "chapter"
            message = current_narrative[0] if current_narrative else current_title
            supporting_points = [
                BriefSourceSupportingPoint(statement=item) for item in current_supporting if item
            ]
            chapters.append(
                BriefSourceChapter(
                    id=chapter_id,
                    title=current_title,
                    message=message,
                    details=current_narrative,
                    supporting_points=supporting_points,
                )
            )
            current_title = None
            current_narrative = []
            current_supporting = []

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("# "):
                title = line[2:].strip()
                continue
            if line.startswith("## "):
                finalize_current()
                current_title = line[3:].strip()
                continue
            if line.startswith("- "):
                if current_title:
                    current_supporting.append(line[2:].strip())
                else:
                    intro_lines.append(line[2:].strip())
                continue
            if current_title:
                current_narrative.append(line)
            else:
                intro_lines.append(line)

        finalize_current()

        story_phases = ["introduction", "problem", "solution", "impact", "next"]
        normalized_chapters: list[BriefSourceChapter] = []
        for index, chapter in enumerate(chapters):
            intent = chapter.intent_tags or []
            if not intent and index < len(story_phases):
                intent = [story_phases[index]]
            normalized_chapters.append(
                chapter.model_copy(
                    update={
                        "intent_tags": intent,
                        "story_hint": story_phases[min(index, len(story_phases) - 1)],
                    }
                )
            )

        meta = BriefSourceMeta(
            title=title or (brief_id or "Brief"),
            brief_id=brief_id,
            objective="\n".join(intro_lines) or None,
        )
        return cls(meta=meta, chapters=normalized_chapters)
