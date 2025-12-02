"""共通モデル定義。"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_JP_FONT = "Meiryo UI"


__all__ = [
    "DEFAULT_JP_FONT",
    "FontSpec",
    "TextboxPosition",
    "TextboxParagraph",
    "TextFramePadding",
    "TextCapacity",
    "TemplateColorPalette",
    "TemplateTextboxDefaults",
    "TemplateTableDefaults",
    "TemplateChartDefaults",
    "TemplateImageDefaults",
    "TemplateStyle",
]


class FontSpec(BaseModel):
    """フォント設定。"""

    name: str = Field(..., description="フォントファミリ名")
    size_pt: float = Field(..., ge=6.0, description="フォントサイズ")
    bold: bool = False
    italic: bool = False
    color_hex: str = Field("#000000", pattern=r"^#?[0-9A-Fa-f]{6}$")

    @field_validator("color_hex")
    @classmethod
    def normalize_hex(cls, value: str) -> str:
        return value if value.startswith("#") else f"#{value}"


class TextboxPosition(BaseModel):
    """テキストボックス位置情報。"""

    model_config = ConfigDict(extra="forbid")

    left_in: float
    top_in: float
    width_in: float
    height_in: float


class TextboxParagraph(BaseModel):
    """段落設定。"""

    model_config = ConfigDict(extra="forbid")

    level: int = Field(0, ge=0, le=5)
    line_spacing_pt: float | None = Field(None, ge=0.0)
    space_before_pt: float | None = Field(None, ge=0.0)
    space_after_pt: float | None = Field(None, ge=0.0)
    align: str | None = Field(
        None, pattern=r"^(left|center|right|justify|distributed)$"
    )
    left_indent_in: float | None = None
    right_indent_in: float | None = None
    first_line_indent_in: float | None = None


class TextFramePadding(BaseModel):
    """テキスト枠余白。"""

    model_config = ConfigDict(extra="forbid")

    left_in: float | None = None
    right_in: float | None = None
    top_in: float | None = None
    bottom_in: float | None = None


class TextCapacity(BaseModel):
    """推定文字容量。"""

    model_config = ConfigDict(extra="forbid")

    total_chars: int = 0
    chars_per_line: int = 0
    max_lines: int = 0


class TemplateColorPalette(BaseModel):
    """テンプレート用カラーパレット。"""

    model_config = ConfigDict(extra="forbid")

    primary: str
    secondary: str
    accent: str
    background: str


class TemplateTextboxDefaults(BaseModel):
    """テンプレートのテキストボックス既定値。"""

    model_config = ConfigDict(extra="forbid")

    fallback_box: TextboxPosition
    font: FontSpec
    paragraph: TextboxParagraph


class TemplateTableDefaults(BaseModel):
    """テンプレートのテーブル既定値。"""

    model_config = ConfigDict(extra="forbid")

    fallback_box: TextboxPosition
    header_font: FontSpec
    header_fill_color: str
    body_font: FontSpec
    body_fill_color: str
    zebra_fill_color: str | None = None


class TemplateChartDefaults(BaseModel):
    """テンプレートのチャート既定値。"""

    model_config = ConfigDict(extra="forbid")

    fallback_box: TextboxPosition
    palette: list[str] = Field(default_factory=list)
    axis_font: FontSpec
    legend_font: FontSpec | None = None
    data_labels_enabled: bool = False
    data_labels_format: str | None = None


class TemplateImageDefaults(BaseModel):
    """テンプレートの画像既定値。"""

    model_config = ConfigDict(extra="forbid")

    fallback_box: TextboxPosition
    sizing: str = Field("fit", pattern=r"^(fit|fill|stretch)$")


class TemplateStyle(BaseModel):
    """テンプレートスタイル定義。"""

    model_config = ConfigDict(extra="forbid")

    heading_font: FontSpec
    body_font: FontSpec
    colors: TemplateColorPalette
    textbox: TemplateTextboxDefaults
    table: TemplateTableDefaults
    chart: TemplateChartDefaults
    image: TemplateImageDefaults

    DEFAULT_THEME: ClassVar[str] = DEFAULT_JP_FONT

    @classmethod
    def default(cls) -> "TemplateStyle":
        """プロジェクト既定のテンプレートスタイルを生成する。"""

        heading = FontSpec(
            name=DEFAULT_JP_FONT,
            size_pt=32.0,
            color_hex="#1A1A1A",
            bold=False,
            italic=False,
        )
        body = FontSpec(
            name=DEFAULT_JP_FONT,
            size_pt=18.0,
            color_hex="#333333",
            bold=False,
            italic=False,
        )
        textbox_paragraph = TextboxParagraph(
            align="left",
            line_spacing_pt=22.0,
            left_indent_in=0.3,
            first_line_indent_in=-0.2,
        )
        textbox_defaults = TemplateTextboxDefaults(
            fallback_box=TextboxPosition(
                left_in=1.0,
                top_in=1.0,
                width_in=8.0,
                height_in=1.5,
            ),
            font=body,
            paragraph=textbox_paragraph,
        )
        table_defaults = TemplateTableDefaults(
            fallback_box=TextboxPosition(
                left_in=1.0,
                top_in=1.5,
                width_in=8.5,
                height_in=3.0,
            ),
            header_font=FontSpec(
                name=DEFAULT_JP_FONT,
                size_pt=18.0,
                color_hex="#FFFFFF",
                bold=True,
                italic=False,
            ),
            header_fill_color="#005BAC",
            body_font=FontSpec(
                name=DEFAULT_JP_FONT,
                size_pt=16.0,
                color_hex="#333333",
                bold=False,
                italic=False,
            ),
            body_fill_color="#FFFFFF",
            zebra_fill_color="#F4F7FB",
        )
        chart_defaults = TemplateChartDefaults(
            fallback_box=TextboxPosition(
                left_in=1.0,
                top_in=1.5,
                width_in=8.5,
                height_in=4.0,
            ),
            palette=[
                "#005BAC",
                "#0097A7",
                "#FF7043",
                "#4CAF50",
                "#7E57C2",
                "#8D6E63",
            ],
            axis_font=FontSpec(
                name=DEFAULT_JP_FONT,
                size_pt=14.0,
                color_hex="#333333",
                bold=False,
                italic=False,
            ),
            data_labels_enabled=True,
            data_labels_format="0",
        )
        image_defaults = TemplateImageDefaults(
            fallback_box=TextboxPosition(
                left_in=1.0,
                top_in=1.75,
                width_in=8.0,
                height_in=4.5,
            ),
            sizing="fit",
        )
        colors = TemplateColorPalette(
            primary="#005BAC",
            secondary="#0097A7",
            accent="#FF7043",
            background="#FFFFFF",
        )
        return cls(
            heading_font=heading,
            body_font=body,
            colors=colors,
            textbox=textbox_defaults,
            table=table_defaults,
            chart=chart_defaults,
            image=image_defaults,
        )
