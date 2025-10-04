"""JSON 入力仕様を表現する Pydantic モデル群。"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator


class FontSpec(BaseModel):
    name: str = Field(..., description="フォントファミリ名")
    size_pt: float = Field(..., ge=6.0, description="フォントサイズ")
    bold: bool = False
    italic: bool = False
    color_hex: str = Field("#000000", pattern=r"^#?[0-9A-Fa-f]{6}$")

    @field_validator("color_hex")
    @classmethod
    def normalize_hex(cls, value: str) -> str:
        return value if value.startswith("#") else f"#{value}"


class SlideBullet(BaseModel):
    id: str
    text: str = Field(..., max_length=200)
    level: int = Field(0, ge=0, le=5)
    font: FontSpec | None = None


class SlideImage(BaseModel):
    id: str
    source: HttpUrl | str
    anchor: str | None = None
    sizing: Literal["fit", "fill", "stretch"] = "fit"
    left_in: float | None = None
    top_in: float | None = None
    width_in: float | None = None
    height_in: float | None = None


class Slide(BaseModel):
    id: str
    layout: str
    title: str | None = None
    subtitle: str | None = None
    notes: str | None = None
    bullets: list[SlideBullet] = Field(default_factory=list)
    images: list[SlideImage] = Field(default_factory=list)


class JobMeta(BaseModel):
    schema_version: str
    title: str
    client: str | None = None
    author: str | None = None
    created_at: str | None = None
    theme: str | None = None
    locale: str = "ja-JP"


class JobAuth(BaseModel):
    created_by: str
    department: str | None = None


class JobSpec(BaseModel):
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


class SpecValidationError(RuntimeError):
    """入力仕様の検証エラー。"""

    def __init__(self, message: str, *, errors: list[dict[str, object]] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []

    @classmethod
    def from_validation_error(cls, exc: ValidationError) -> "SpecValidationError":
        return cls("入力仕様の検証に失敗しました", errors=exc.errors())
