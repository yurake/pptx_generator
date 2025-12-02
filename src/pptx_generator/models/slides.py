"""スライド関連モデル。"""

from __future__ import annotations

from typing import Iterable, Iterator, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .common import FontSpec, TextCapacity, TextFramePadding, TextboxParagraph, TextboxPosition

__all__ = [
    "SlideBullet",
    "SlideBulletGroup",
    "SlideImage",
    "TableStyle",
    "SlideTable",
    "ChartSeries",
    "ChartOptions",
    "SlideChart",
    "SlideTextbox",
    "Slide",
]


class SlideBullet(BaseModel):
    """箇条書き項目。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    level: int = Field(0, ge=0, le=5)
    font: FontSpec | None = None


class SlideBulletGroup(BaseModel):
    """箇条書きグループ。"""

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
    """スライド内の画像。"""

    id: str
    source: str
    anchor: str | None = None
    sizing: Literal["fit", "fill", "stretch"] = "fit"
    left_in: float | None = None
    top_in: float | None = None
    width_in: float | None = None
    height_in: float | None = None


class TableStyle(BaseModel):
    """テーブルスタイル設定。"""

    header_fill: str | None = Field(None, pattern=r"^#?[0-9A-Fa-f]{6}$")
    zebra: bool = False

    @field_validator("header_fill")
    @classmethod
    def normalize_header_fill(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value if value.startswith("#") else f"#{value}"


class SlideTable(BaseModel):
    """スライド内の表。"""

    id: str
    anchor: str | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[list[str | int | float]] = Field(default_factory=list)
    style: TableStyle | None = None


class ChartSeries(BaseModel):
    """チャートの系列情報。"""

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
    """チャート表示オプション。"""

    data_labels: bool = False
    y_axis_format: str | None = None


class SlideChart(BaseModel):
    """スライド内のチャート。"""

    id: str
    anchor: str | None = None
    type: str
    categories: list[str] = Field(default_factory=list)
    series: list[ChartSeries] = Field(default_factory=list)
    options: ChartOptions | None = None


class SlideTextbox(BaseModel):
    """スライド内のテキストボックス。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    anchor: str | None = None
    position: TextboxPosition | None = None
    font: FontSpec | None = None
    paragraph: TextboxParagraph | None = None
    text_frame_padding: TextFramePadding | None = None
    text_capacity: TextCapacity | None = None


class Slide(BaseModel):
    """スライド構成要素。"""

    id: str
    layout: str
    title: str | None = None
    subtitle: str | None = None
    notes: str | None = None
    bullets: list[SlideBulletGroup] = Field(default_factory=list)
    images: list[SlideImage] = Field(default_factory=list)
    tables: list[SlideTable] = Field(default_factory=list)
    charts: list[SlideChart] = Field(default_factory=list)
    textboxes: list[SlideTextbox] = Field(default_factory=list)
    auto_draw_anchors: list[str] = Field(default_factory=list)
    auto_draw_boxes: dict[str, TextboxPosition] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    def iter_bullet_groups(self) -> Iterable[SlideBulletGroup]:
        """箇条書きグループを順序通りに返す。"""

        return tuple(self.bullets)

    def iter_bullets(self) -> Iterator[SlideBullet]:
        """すべての箇条書き項目を順序通りにイテレートする。"""

        for group in self.bullets:
            yield from group.items
