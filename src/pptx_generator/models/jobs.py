"""ジョブ仕様関連モデル。"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .common import FontSpec, TextCapacity, TextFramePadding, TextboxParagraph
from .exceptions import SpecValidationError
from .slides import Slide

__all__ = [
    "JobMeta",
    "JobAuth",
    "JobSpec",
    "JobSpecScaffoldBounds",
    "JobSpecScaffoldPlaceholder",
    "JobSpecScaffoldSlide",
    "JobSpecScaffoldMeta",
    "JobSpecScaffold",
    "JobSpecScaffoldPlaceholderKind",
]

JobSpecScaffoldPlaceholderKind = Literal["text", "image", "table", "chart", "other"]


class JobMeta(BaseModel):
    """ジョブメタ情報。"""

    schema_version: str
    title: str
    client: str | None = None
    author: str | None = None
    created_at: str | None = None
    theme: str | None = None
    locale: str = "ja-JP"
    layout_count: int | None = None
    layouts_path: str | None = None
    template_path: str | None = None
    template_id: str | None = None
    template_spec_path: str | None = None


class JobAuth(BaseModel):
    """ジョブ認証情報。"""

    created_by: str
    department: str | None = None


class JobSpec(BaseModel):
    """ジョブ仕様。"""

    meta: JobMeta
    auth: JobAuth
    slides: list[Slide] = Field(default_factory=list)

    @classmethod
    def parse_file(cls, path: str | Path) -> "JobSpec":
        source = Path(path).read_text(encoding="utf-8")
        try:
            return cls.model_validate_json(source)
        except ValidationError as exc:
            raise SpecValidationError.from_validation_error(exc) from exc


class JobSpecScaffoldBounds(BaseModel):
    """スキャフォールドの領域情報。"""

    model_config = ConfigDict(extra="forbid")

    left_in: float
    top_in: float
    width_in: float
    height_in: float


class JobSpecScaffoldPlaceholder(BaseModel):
    """スキャフォールドでのプレースホルダー情報。"""

    model_config = ConfigDict(extra="forbid")

    anchor: str
    kind: JobSpecScaffoldPlaceholderKind
    placeholder_type: str | None = None
    shape_type: str | None = None
    is_placeholder: bool = False
    bounds: JobSpecScaffoldBounds
    sample_text: str | None = None
    notes: list[str] = Field(default_factory=list)
    auto_draw: bool = False
    font: FontSpec | None = None
    paragraph: TextboxParagraph | None = None
    text_frame_padding: TextFramePadding | None = None
    text_capacity: TextCapacity | None = None


class JobSpecScaffoldSlide(BaseModel):
    """スキャフォールドのスライド情報。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    layout: str
    sequence: int
    placeholders: list[JobSpecScaffoldPlaceholder] = Field(default_factory=list)


class JobSpecScaffoldMeta(BaseModel):
    """スキャフォールドに付随するメタ情報。"""

    model_config = ConfigDict(extra="forbid")

    schema_version: str
    template_path: str
    template_id: str
    generated_at: str
    layout_count: int
    layouts_path: str | None = None
    template_spec_path: str | None = None
    template_source: Literal["slide", "template"] | None = Field(
        None,
        description="テンプレ抽出ソース。静的モードで実スライドを使用した場合は 'slide'。",
    )


class JobSpecScaffold(BaseModel):
    """スキャフォールド全体。"""

    model_config = ConfigDict(extra="forbid")

    meta: JobSpecScaffoldMeta
    slides: list[JobSpecScaffoldSlide] = Field(default_factory=list)

    @field_validator("slides")
    @classmethod
    def ensure_slides_not_empty(cls, value: list[JobSpecScaffoldSlide]) -> list[JobSpecScaffoldSlide]:
        if not value:
            raise ValueError("scaffold には 1 枚以上の slide が必要です")
        return value
