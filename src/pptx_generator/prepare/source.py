from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

PrepareEvidenceType = Literal["url", "source_id", "note"]


class PrepareSourceMeta(BaseModel):
    """プレペア入力のメタ情報。"""

    title: str
    prepare_id: str | None = None
    client: str | None = None
    objective: str | None = None
    locale: str | None = "ja-JP"


class PrepareSourceSupportingPoint(BaseModel):
    """入力定義の支援ポイント。"""

    statement: str
    evidence_type: PrepareEvidenceType | None = None
    evidence_value: str | None = None


class PrepareSourceChapter(BaseModel):
    """入力定義の章情報。"""

    id: str = Field(..., pattern=r"^[a-z0-9\\-]+$")
    title: str
    message: str | None = None
    details: list[str] = Field(default_factory=list)
    supporting_points: list[PrepareSourceSupportingPoint] = Field(default_factory=list)
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


class PrepareSourceDocument(BaseModel):
    """プレペア入力ドキュメント。"""

    meta: PrepareSourceMeta
    chapters: list[PrepareSourceChapter] = Field(default_factory=list)
    raw_text: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "PrepareSourceDocument":
        return cls.model_validate(payload)

    @classmethod
    def parse_file(cls, path: str | Path) -> "PrepareSourceDocument":
        source_path = Path(path)
        text = Path.read_text(source_path, encoding="utf-8")
        if source_path.suffix.lower() in {".json", ".jsonc"}:
            payload = json.loads(text)
            return cls.from_payload(payload)
        return cls._from_markdown(text, prepare_id=source_path.stem)

    @classmethod
    def _from_markdown(cls, text: str, *, prepare_id: str | None = None) -> "PrepareSourceDocument":
        lines = text.splitlines()
        title: str | None = None
        intro_lines: list[str] = []
        chapters: list[PrepareSourceChapter] = []

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
                PrepareSourceSupportingPoint(statement=item) for item in current_supporting if item
            ]
            chapters.append(
                PrepareSourceChapter(
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

        normalized_chapters: list[PrepareSourceChapter] = []
        for chapter in chapters:
            normalized_chapters.append(
                chapter.model_copy(
                    update={
                        "intent_tags": [tag for tag in chapter.intent_tags if tag],
                    }
                )
            )

        meta = PrepareSourceMeta(
            title=title or (prepare_id or "Prepare"),
            prepare_id=prepare_id,
            objective="\n".join(intro_lines) or None,
        )
        return cls(meta=meta, chapters=normalized_chapters, raw_text=text)
