"""Branding configuration helpers."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from .coercers import coerce_float, coerce_hex, coerce_int, ensure_hex_prefix

__all__ = [
    "BrandingFont",
    "ParagraphStyle",
    "BoxSpec",
    "TableHeaderStyle",
    "TableBodyStyle",
    "TableComponentStyle",
    "ChartDataLabelsStyle",
    "ChartAxisStyle",
    "ChartComponentStyle",
    "ImageComponentStyle",
    "TextboxComponentStyle",
    "BrandingComponents",
    "ColorPalette",
    "BrandingTheme",
    "PlacementStyle",
    "LayoutStyle",
    "BrandingConfig",
]

logger = logging.getLogger(__name__)


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
    def load(cls, path: Path | str) -> "BrandingConfig":
        path = Path(path)
        logger.info("Loading branding config from %s", path.resolve())
        data = json.loads(path.read_text(encoding="utf-8"))
        config = cls.from_dict(data)
        logger.info("Loaded branding config from %s", path.resolve())
        return config

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "BrandingConfig":
        defaults = cls.default()

        version = str(data.get("version") or defaults.version)

        theme_payload = data.get("theme", {}) if isinstance(data.get("theme"), dict) else {}
        fonts_payload = theme_payload.get("fonts", {}) if isinstance(theme_payload, dict) else {}
        colors_payload = theme_payload.get("colors", {}) if isinstance(theme_payload, dict) else {}

        heading_font = _parse_font(fonts_payload.get("heading"), defaults.theme.heading)
        body_font = _parse_font(fonts_payload.get("body"), defaults.theme.body)
        colors = ColorPalette(
            primary=ensure_hex_prefix(colors_payload.get("primary", defaults.theme.colors.primary)),
            secondary=ensure_hex_prefix(colors_payload.get("secondary", defaults.theme.colors.secondary)),
            accent=ensure_hex_prefix(colors_payload.get("accent", defaults.theme.colors.accent)),
            background=ensure_hex_prefix(colors_payload.get("background", defaults.theme.colors.background)),
        )
        theme = BrandingTheme(heading=heading_font, body=body_font, colors=colors)

        components_payload = data.get("components", {}) if isinstance(data.get("components"), dict) else {}
        components = BrandingComponents(
            table=_parse_table_component(components_payload.get("table"), defaults.components.table),
            chart=_parse_chart_component(components_payload.get("chart"), defaults.components.chart),
            image=_parse_image_component(components_payload.get("image"), defaults.components.image),
            textbox=_parse_textbox_component(components_payload.get("textbox"), defaults.components.textbox),
        )

        layouts_payload = data.get("layouts", {})
        layouts: dict[str, LayoutStyle] = {}
        if isinstance(layouts_payload, dict):
            for layout_name, layout_data in layouts_payload.items():
                if not isinstance(layout_data, dict):
                    continue
                placements_payload = layout_data.get("placements", {})
                placements: dict[str, PlacementStyle] = {}
                if isinstance(placements_payload, dict):
                    for placement_key, placement_data in placements_payload.items():
                        if not isinstance(placement_data, dict):
                            continue
                        placements[placement_key] = PlacementStyle(
                            box=_parse_box_optional(placement_data.get("box")),
                            font=_parse_font_optional(placement_data.get("font"), defaults.theme.body),
                            paragraph=_parse_paragraph_optional(placement_data.get("paragraph")),
                        )
                layouts[layout_name] = LayoutStyle(placements=placements)

        return cls(version=version, theme=theme, components=components, layouts=layouts)

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
                font=BrandingFont(name="Meiryo UI", size_pt=18.0, color_hex="#FFFFFF", bold=True),
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
            axis=ChartAxisStyle(font=BrandingFont(name="Meiryo UI", size_pt=14.0, color_hex="#333333")),
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
            components=BrandingComponents(table=table, chart=chart, image=image, textbox=textbox),
            layouts={},
        )

    def resolve_fallback_box(
        self,
        element_type: str,
        *,
        layout: str | None = None,
        placement_key: str | None = None,
    ) -> BoxSpec:
        layout_style = self.layouts.get(layout or "") if layout else None
        if layout_style and placement_key:
            placement = layout_style.placements.get(placement_key)
            if placement and placement.box:
                return placement.box

        if element_type == "table":
            return self.components.table.fallback_box
        if element_type == "chart":
            return self.components.chart.fallback_box
        if element_type == "image":
            return self.components.image.fallback_box
        if element_type == "textbox":
            return self.components.textbox.fallback_box
        raise ValueError(f"unknown element_type: {element_type}")

    def resolve_layout_font(self, *, layout: str, placement_key: str, default: BrandingFont) -> BrandingFont:
        if not placement_key:
            return default
        layout_style = self.layouts.get(layout)
        if not layout_style:
            return default
        placement = layout_style.placements.get(placement_key)
        return placement.font if placement and placement.font else default

    def resolve_layout_paragraph(
        self,
        *,
        layout: str,
        placement_key: str,
        default: ParagraphStyle,
    ) -> ParagraphStyle:
        if not placement_key:
            return default
        layout_style = self.layouts.get(layout)
        if not layout_style:
            return default
        placement = layout_style.placements.get(placement_key)
        return placement.paragraph if placement and placement.paragraph else default


def _parse_font(payload: object, default: BrandingFont) -> BrandingFont:
    if not isinstance(payload, dict):
        return default
    return BrandingFont(
        name=str(payload.get("name", default.name)),
        size_pt=float(payload.get("size_pt", default.size_pt)),
        color_hex=ensure_hex_prefix(str(payload.get("color_hex", default.color_hex))),
        bold=bool(payload.get("bold", default.bold)),
        italic=bool(payload.get("italic", default.italic)),
    )


def _parse_font_optional(payload: object, default: BrandingFont | None = None) -> BrandingFont | None:
    if payload is None:
        return None
    base = default or BrandingFont(name="", size_pt=12.0, color_hex="#000000")
    return _parse_font(payload, base)


def _parse_paragraph(payload: object, default: ParagraphStyle) -> ParagraphStyle:
    if not isinstance(payload, dict):
        return default
    return ParagraphStyle(
        align=payload.get("align", default.align),
        line_spacing_pt=coerce_float(payload.get("line_spacing_pt", default.line_spacing_pt)),
        space_before_pt=coerce_float(payload.get("space_before_pt", default.space_before_pt)),
        space_after_pt=coerce_float(payload.get("space_after_pt", default.space_after_pt)),
        level=coerce_int(payload.get("level", default.level)),
        left_indent_in=coerce_float(payload.get("left_indent_in", default.left_indent_in)),
        right_indent_in=coerce_float(payload.get("right_indent_in", default.right_indent_in)),
        first_line_indent_in=coerce_float(payload.get("first_line_indent_in", default.first_line_indent_in)),
    )


def _parse_paragraph_optional(payload: object) -> ParagraphStyle | None:
    if payload is None:
        return None
    return _parse_paragraph(payload, ParagraphStyle())


def _parse_box(payload: object, default: BoxSpec) -> BoxSpec:
    if not isinstance(payload, dict):
        return default
    return BoxSpec(
        left_in=float(payload.get("left_in", default.left_in)),
        top_in=float(payload.get("top_in", default.top_in)),
        width_in=float(payload.get("width_in", default.width_in)),
        height_in=float(payload.get("height_in", default.height_in)),
    )


def _parse_box_optional(payload: object) -> BoxSpec | None:
    if payload is None:
        return None
    default = BoxSpec(left_in=0.0, top_in=0.0, width_in=0.0, height_in=0.0)
    return _parse_box(payload, default)


def _parse_table_component(payload: object, default: TableComponentStyle) -> TableComponentStyle:
    if not isinstance(payload, dict):
        return default
    header_payload = payload.get("header", {})
    body_payload = payload.get("body", {})

    return TableComponentStyle(
        fallback_box=_parse_box(payload.get("fallback_box"), default.fallback_box),
        header=TableHeaderStyle(
            font=_parse_font(header_payload.get("font"), default.header.font),
            fill_color=ensure_hex_prefix(header_payload.get("fill_color") or default.header.fill_color),
        ),
        body=TableBodyStyle(
            font=_parse_font(body_payload.get("font"), default.body.font),
            fill_color=ensure_hex_prefix(body_payload.get("fill_color") or default.body.fill_color),
            zebra_fill_color=_resolve_optional_color(
                body_payload.get("zebra_fill_color"), default.body.zebra_fill_color
            ),
        ),
    )


def _parse_chart_component(payload: object, default: ChartComponentStyle) -> ChartComponentStyle:
    if not isinstance(payload, dict):
        return default

    palette_payload = payload.get("palette")
    if isinstance(palette_payload, (list, tuple)) and palette_payload:
        palette = tuple(ensure_hex_prefix(str(color)) for color in palette_payload)
    else:
        palette = default.palette

    data_labels_payload = payload.get("data_labels", {})
    if isinstance(data_labels_payload, dict):
        data_labels = ChartDataLabelsStyle(
            enabled=bool(data_labels_payload.get("enabled", default.data_labels.enabled)),
            format=data_labels_payload.get("format", default.data_labels.format),
        )
    else:
        data_labels = default.data_labels

    axis_payload = payload.get("axis", {})
    axis_font = (
        _parse_font(axis_payload.get("font"), default.axis.font)
        if isinstance(axis_payload, dict)
        else default.axis.font
    )

    sizing_box = _parse_box(payload.get("fallback_box"), default.fallback_box)

    return ChartComponentStyle(
        fallback_box=sizing_box,
        palette=palette,
        data_labels=data_labels,
        axis=ChartAxisStyle(font=axis_font),
    )


def _parse_image_component(payload: object, default: ImageComponentStyle) -> ImageComponentStyle:
    if not isinstance(payload, dict):
        return default

    fallback_box = _parse_box(payload.get("fallback_box"), default.fallback_box)
    sizing = str(payload.get("sizing", default.sizing)).lower()
    if sizing not in {"fit", "fill", "stretch"}:
        sizing = default.sizing

    return ImageComponentStyle(fallback_box=fallback_box, sizing=sizing)


def _parse_textbox_component(payload: object, default: TextboxComponentStyle) -> TextboxComponentStyle:
    if not isinstance(payload, dict):
        return default

    fallback_box = _parse_box(payload.get("fallback_box"), default.fallback_box)
    font = _parse_font(payload.get("font"), default.font)
    paragraph = _parse_paragraph(payload.get("paragraph"), default.paragraph)

    return TextboxComponentStyle(fallback_box=fallback_box, font=font, paragraph=paragraph)


def _resolve_optional_color(value: object, default: str | None) -> str | None:
    if value in (None, ""):
        return default
    return ensure_hex_prefix(str(value))

