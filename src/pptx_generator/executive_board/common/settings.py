"""設定ファイルの読み込みユーティリティ（簡易版）。

pptx_generator_scheduleパッケージ用の最小限の設定クラス。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path


logger = logging.getLogger(__name__)


def _ensure_hex_prefix(value: str) -> str:
    normalized = value if value.startswith("#") else f"#{value}"
    return normalized.upper()


@dataclass(slots=True)
class BrandingFont:
    name: str
    size_pt: float
    color_hex: str
    bold: bool = False
    italic: bool = False


@dataclass(slots=True)
class ParagraphStyle:
    align: str | None = None
    line_spacing_pt: float | None = None
    space_before_pt: float | None = None
    space_after_pt: float | None = None
    level: int | None = None
    left_indent_in: float | None = None
    right_indent_in: float | None = None
    first_line_indent_in: float | None = None


@dataclass(slots=True)
class BoxSpec:
    left_in: float
    top_in: float
    width_in: float
    height_in: float


@dataclass(slots=True)
class TableHeaderStyle:
    font: BrandingFont
    fill_color: str


@dataclass(slots=True)
class TableBodyStyle:
    font: BrandingFont
    fill_color: str
    zebra_fill_color: str | None = None


@dataclass(slots=True)
class TableComponentStyle:
    fallback_box: BoxSpec
    header: TableHeaderStyle
    body: TableBodyStyle


@dataclass(slots=True)
class ChartDataLabelsStyle:
    enabled: bool
    format: str | None


@dataclass(slots=True)
class ChartAxisStyle:
    font: BrandingFont


@dataclass(slots=True)
class ChartComponentStyle:
    fallback_box: BoxSpec
    palette: tuple[str, ...]
    data_labels: ChartDataLabelsStyle
    axis: ChartAxisStyle


@dataclass(slots=True)
class ImageComponentStyle:
    fallback_box: BoxSpec
    sizing: str


@dataclass(slots=True)
class TextboxComponentStyle:
    fallback_box: BoxSpec
    font: BrandingFont
    paragraph: ParagraphStyle


@dataclass(slots=True)
class BrandingComponents:
    table: TableComponentStyle
    chart: ChartComponentStyle
    image: ImageComponentStyle
    textbox: TextboxComponentStyle


@dataclass(slots=True)
class ColorPalette:
    primary: str
    secondary: str
    accent: str
    background: str


@dataclass(slots=True)
class BrandingTheme:
    heading: BrandingFont
    body: BrandingFont
    colors: ColorPalette


@dataclass(slots=True)
class PlacementStyle:
    box: BoxSpec | None = None
    font: BrandingFont | None = None
    paragraph: ParagraphStyle | None = None


@dataclass(slots=True)
class LayoutStyle:
    placements: dict[str, PlacementStyle] = field(default_factory=dict)


@dataclass(slots=True)
class BrandingConfig:
    version: str
    theme: BrandingTheme
    components: BrandingComponents
    layouts: dict[str, LayoutStyle]

    @property
    def heading_font(self) -> BrandingFont:
        return self.theme.heading

    @property
    def body_font(self) -> BrandingFont:
        return self.theme.body

    @property
    def primary_color(self) -> str:
        return self.theme.colors.primary

    @property
    def secondary_color(self) -> str:
        return self.theme.colors.secondary

    @property
    def accent_color(self) -> str:
        return self.theme.colors.accent

    @property
    def background_color(self) -> str:
        return self.theme.colors.background

    @classmethod
    def load(cls, path: Path) -> "BrandingConfig":
        logger.info("Loading branding config from %s", path.resolve())
        data = json.loads(path.read_text(encoding="utf-8"))
        config = cls.from_dict(data)
        logger.info("Loaded branding config from %s", path.resolve())
        return config

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "BrandingConfig":
        defaults = cls.default()

        version = str(data.get("version") or defaults.version)

        theme_payload = data.get("theme", {})
        fonts_payload = theme_payload.get("fonts", {}) if isinstance(theme_payload, dict) else {}
        colors_payload = theme_payload.get("colors", {}) if isinstance(theme_payload, dict) else {}

        heading_font = _parse_font(fonts_payload.get("heading"), defaults.theme.heading)
        body_font = _parse_font(fonts_payload.get("body"), defaults.theme.body)
        colors = ColorPalette(
            primary=_ensure_hex_prefix(colors_payload.get("primary", defaults.theme.colors.primary)),
            secondary=_ensure_hex_prefix(
                colors_payload.get("secondary", defaults.theme.colors.secondary)
            ),
            accent=_ensure_hex_prefix(colors_payload.get("accent", defaults.theme.colors.accent)),
            background=_ensure_hex_prefix(
                colors_payload.get("background", defaults.theme.colors.background)
            ),
        )
        theme = BrandingTheme(heading=heading_font, body=body_font, colors=colors)

        components = defaults.components

        return cls(
            version=version,
            theme=theme,
            components=components,
            layouts={},
        )

    @classmethod
    def default(cls) -> "BrandingConfig":
        heading = BrandingFont(name="Meiryo UI", size_pt=32.0, color_hex="#1A1A1A")
        body = BrandingFont(name="Meiryo UI", size_pt=18.0, color_hex="#333333")
        colors = ColorPalette(
            primary="#005BAC",
            secondary="#0097A7",
            accent="#FF7043",
            background="#FFFFFF",
        )
        table = TableComponentStyle(
            fallback_box=BoxSpec(left_in=1.0, top_in=1.5, width_in=8.5, height_in=3.0),
            header=TableHeaderStyle(
                font=BrandingFont(
                    name="Meiryo UI",
                    size_pt=18.0,
                    color_hex="#FFFFFF",
                    bold=True,
                ),
                fill_color="#005BAC",
            ),
            body=TableBodyStyle(
                font=BrandingFont(name="Meiryo UI", size_pt=16.0, color_hex="#333333"),
                fill_color="#FFFFFF",
                zebra_fill_color="#F4F7FB",
            ),
        )
        chart = ChartComponentStyle(
            fallback_box=BoxSpec(left_in=1.0, top_in=1.5, width_in=8.5, height_in=4.0),
            palette=(
                "#005BAC",
                "#0097A7",
                "#FF7043",
                "#4CAF50",
                "#7E57C2",
                "#8D6E63",
            ),
            data_labels=ChartDataLabelsStyle(enabled=True, format="0"),
            axis=ChartAxisStyle(
                font=BrandingFont(name="Meiryo UI", size_pt=14.0, color_hex="#333333")
            ),
        )
        image = ImageComponentStyle(
            fallback_box=BoxSpec(left_in=1.0, top_in=1.75, width_in=8.0, height_in=4.5),
            sizing="fit",
        )
        textbox = TextboxComponentStyle(
            fallback_box=BoxSpec(left_in=1.0, top_in=1.0, width_in=8.0, height_in=1.5),
            font=BrandingFont(name="Meiryo UI", size_pt=18.0, color_hex="#333333"),
            paragraph=ParagraphStyle(
                align="left",
                line_spacing_pt=22.0,
                left_indent_in=0.3,
                first_line_indent_in=-0.2,
            ),
        )

        return cls(
            version="layout-style-v1",
            theme=BrandingTheme(heading=heading, body=body, colors=colors),
            components=BrandingComponents(
                table=table,
                chart=chart,
                image=image,
                textbox=textbox,
            ),
            layouts={},
        )


def _parse_font(payload: object, default: BrandingFont) -> BrandingFont:
    if not isinstance(payload, dict):
        return default
    return BrandingFont(
        name=str(payload.get("name", default.name)),
        size_pt=float(payload.get("size_pt", default.size_pt)),
        color_hex=_ensure_hex_prefix(str(payload.get("color_hex", default.color_hex))),
        bold=bool(payload.get("bold", default.bold)),
        italic=bool(payload.get("italic", default.italic)),
    )