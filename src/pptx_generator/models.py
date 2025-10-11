"""JSON 入力仕様を表現する Pydantic モデル群。"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    ValidationError,
    field_validator,
)


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
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str = Field(..., max_length=200)
    level: int = Field(0, ge=0, le=5)
    font: FontSpec | None = None


class SlideBulletGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anchor: str | None = None
    items: list[SlideBullet] = Field(default_factory=list)

    @field_validator("items")
    @classmethod
    def ensure_items_not_empty(cls, value: list[SlideBullet]) -> list[SlideBullet]:
        if not value:
            raise ValueError("items には 1 つ以上の bullet を指定してください")
        return value


class SlideImage(BaseModel):
    id: str
    source: HttpUrl | str
    anchor: str | None = None
    sizing: Literal["fit", "fill", "stretch"] = "fit"
    left_in: float | None = None
    top_in: float | None = None
    width_in: float | None = None
    height_in: float | None = None


class TableStyle(BaseModel):
    header_fill: str | None = Field(None, pattern=r"^#?[0-9A-Fa-f]{6}$")
    zebra: bool = False

    @field_validator("header_fill")
    @classmethod
    def normalize_header_fill(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value if value.startswith("#") else f"#{value}"


class SlideTable(BaseModel):
    id: str
    anchor: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[list[str | int | float]] = Field(default_factory=list)
    style: TableStyle | None = None


class ChartSeries(BaseModel):
    name: str
    values: list[int | float] = Field(default_factory=list)
    color_hex: str | None = Field(None, pattern=r"^#?[0-9A-Fa-f]{6}$")

    @field_validator("color_hex")
    @classmethod
    def normalize_color(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value if value.startswith("#") else f"#{value}"


class ChartOptions(BaseModel):
    data_labels: bool = False
    y_axis_format: str | None = None


class SlideChart(BaseModel):
    id: str
    anchor: str | None = None
    type: str
    categories: list[str] = Field(default_factory=list)
    series: list[ChartSeries] = Field(default_factory=list)
    options: ChartOptions | None = None


class Slide(BaseModel):
    id: str
    layout: str
    title: str | None = None
    subtitle: str | None = None
    notes: str | None = None
    bullets: list[SlideBulletGroup] = Field(default_factory=list)
    images: list[SlideImage] = Field(default_factory=list)
    tables: list[SlideTable] = Field(default_factory=list)
    charts: list[SlideChart] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    def iter_bullet_groups(self) -> Iterable[SlideBulletGroup]:
        """箇条書きグループを順序通りに返す。"""

        return tuple(self.bullets)

    def iter_bullets(self) -> Iterator[SlideBullet]:
        """すべての箇条書き項目を順序通りにイテレートする。"""

        for group in self.bullets:
            yield from group.items


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

    def __init__(
        self, message: str, *, errors: list[dict[str, object]] | None = None
    ) -> None:
        super().__init__(message)
        self.errors = errors or []

    @classmethod
    def from_validation_error(cls, exc: ValidationError) -> "SpecValidationError":
        return cls("入力仕様の検証に失敗しました", errors=exc.errors())


# テンプレート抽出用モデル

class ShapeInfo(BaseModel):
    """図形情報を表現するモデル。"""
    
    name: str = Field(..., description="図形名（アンカー名）")
    shape_type: str = Field(..., description="図形種別")
    left_in: float = Field(..., description="左端位置（インチ）")
    top_in: float = Field(..., description="上端位置（インチ）")
    width_in: float = Field(..., description="幅（インチ）")
    height_in: float = Field(..., description="高さ（インチ）")
    text: str | None = Field(None, description="初期テキスト")
    placeholder_type: str | None = Field(None, description="プレースホルダー種別")
    is_placeholder: bool = Field(False, description="プレースホルダーかどうか")
    error: str | None = Field(None, description="抽出時のエラー")
    missing_fields: list[str] = Field(default_factory=list, description="欠落フィールド")
    conflict: str | None = Field(None, description="SlideBullet拡張仕様との競合")


class LayoutInfo(BaseModel):
    """レイアウト情報を表現するモデル。"""
    
    name: str = Field(..., description="レイアウト名")
    anchors: list[ShapeInfo] = Field(default_factory=list, description="図形・プレースホルダー一覧")
    error: str | None = Field(None, description="レイアウト抽出時のエラー")


class TemplateSpec(BaseModel):
    """テンプレート仕様全体を表現するモデル。"""
    
    template_path: str = Field(..., description="テンプレートファイルパス")
    extracted_at: str = Field(..., description="抽出日時（ISO8601）")
    layouts: list[LayoutInfo] = Field(default_factory=list, description="レイアウト一覧")
    warnings: list[str] = Field(default_factory=list, description="警告メッセージ")
    errors: list[str] = Field(default_factory=list, description="エラーメッセージ")
