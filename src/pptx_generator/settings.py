"""設定ファイルの読み込みユーティリティ。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path


logger = logging.getLogger(__name__)


def _ensure_hex_prefix(value: str) -> str:
    normalized = value if value.startswith("#") else f"#{value}"
    return normalized.upper()


def _maybe_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _maybe_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _maybe_hex(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return _ensure_hex_prefix(value)


@dataclass(slots=True)
class AnalyzerRuleConfig:
    min_font_size: float | None = None
    default_font_size: float | None = None
    default_font_color: str | None = None
    preferred_text_color: str | None = None
    background_color: str | None = None
    min_contrast_ratio: float | None = None
    large_text_min_contrast: float | None = None
    large_text_threshold_pt: float | None = None
    margin_in: float | None = None
    slide_width_in: float | None = None
    slide_height_in: float | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> "AnalyzerRuleConfig":
        if not payload:
            return cls()
        return cls(
            min_font_size=_maybe_float(payload.get("min_font_size")),
            default_font_size=_maybe_float(payload.get("default_font_size")),
            default_font_color=_maybe_hex(payload.get("default_font_color")),
            preferred_text_color=_maybe_hex(payload.get("preferred_text_color")),
            background_color=_maybe_hex(payload.get("background_color")),
            min_contrast_ratio=_maybe_float(payload.get("min_contrast_ratio")),
            large_text_min_contrast=_maybe_float(payload.get("large_text_min_contrast")),
            large_text_threshold_pt=_maybe_float(payload.get("large_text_threshold_pt")),
            margin_in=_maybe_float(payload.get("margin_in")),
            slide_width_in=_maybe_float(payload.get("slide_width_in")),
            slide_height_in=_maybe_float(payload.get("slide_height_in")),
        )


@dataclass(slots=True)
class RefinerRuleConfig:
    enable_bullet_reindent: bool = True
    enable_font_raise: bool = False
    min_font_size: float | None = None
    enable_color_adjust: bool = False
    preferred_text_color: str | None = None
    fallback_font_color: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> "RefinerRuleConfig":
        if not payload:
            return cls()

        def _maybe_bool(value: object, default: bool) -> bool:
            if isinstance(value, bool):
                return value
            return default

        return cls(
            enable_bullet_reindent=_maybe_bool(payload.get("enable_bullet_reindent"), True),
            enable_font_raise=_maybe_bool(payload.get("enable_font_raise"), False),
            min_font_size=_maybe_float(payload.get("min_font_size")),
            enable_color_adjust=_maybe_bool(payload.get("enable_color_adjust"), False),
            preferred_text_color=_maybe_hex(payload.get("preferred_text_color")),
            fallback_font_color=_maybe_hex(payload.get("fallback_font_color")),
        )


@dataclass(slots=True)
class PolisherRuleConfig:
    enabled: bool = False
    executable: str | None = None
    rules_path: str | None = None
    timeout_sec: int = 90
    arguments: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, payload: dict[str, object] | None) -> "PolisherRuleConfig":
        if not payload:
            return cls()

        def _maybe_bool(value: object, default: bool) -> bool:
            if isinstance(value, bool):
                return value
            return default

        def _maybe_str(value: object) -> str | None:
            if isinstance(value, str) and value.strip():
                return value
            return None

        def _maybe_args(value: object) -> tuple[str, ...]:
            if isinstance(value, (list, tuple)):
                result: list[str] = []
                for item in value:
                    if isinstance(item, str) and item.strip():
                        result.append(item)
                return tuple(result)
            if isinstance(value, str) and value.strip():
                return (value,)
            return ()

        timeout = _maybe_int(payload.get("timeout_sec"))
        if timeout is None or timeout <= 0:
            timeout = 90

        return cls(
            enabled=_maybe_bool(payload.get("enabled"), False),
            executable=_maybe_str(payload.get("executable")),
            rules_path=_maybe_str(payload.get("rules_path")),
            timeout_sec=timeout,
            arguments=_maybe_args(payload.get("arguments")),
        )


@dataclass(slots=True)
class RulesConfig:
    max_title_length: int = 25
    max_bullet_length: int = 120
    max_bullet_level: int = 3
    forbidden_words: tuple[str, ...] = ()
    analyzer: AnalyzerRuleConfig = field(default_factory=AnalyzerRuleConfig)
    refiner: RefinerRuleConfig = field(default_factory=RefinerRuleConfig)
    polisher: PolisherRuleConfig = field(default_factory=PolisherRuleConfig)

    @classmethod
    def load(cls, path: Path) -> "RulesConfig":
        logger.info("Loading rules config from %s", path.resolve())
        data = json.loads(path.read_text(encoding="utf-8"))
        title = data.get("title", {})
        bullet = data.get("bullet", {})
        defaults = cls()
        analyzer = AnalyzerRuleConfig.from_dict(data.get("analyzer", {}))
        refiner = RefinerRuleConfig.from_dict(data.get("refiner", {}))
        polisher = PolisherRuleConfig.from_dict(data.get("polisher", {}))
        config = cls(
            max_title_length=title.get("max_length", defaults.max_title_length),
            max_bullet_length=bullet.get("max_length", defaults.max_bullet_length),
            max_bullet_level=bullet.get("max_level", defaults.max_bullet_level),
            forbidden_words=tuple(data.get("forbidden_words", defaults.forbidden_words)),
            analyzer=analyzer,
            refiner=refiner,
            polisher=polisher,
        )
        logger.info("Loaded rules config from %s", path.resolve())
        return config


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

        components_payload = data.get("components", {}) if isinstance(data.get("components"), dict) else {}

        table = _parse_table_component(
            components_payload.get("table", {}),
            defaults.components.table,
        )
        chart = _parse_chart_component(
            components_payload.get("chart", {}),
            defaults.components.chart,
        )
        image = _parse_image_component(
            components_payload.get("image", {}),
            defaults.components.image,
        )
        textbox = _parse_textbox_component(
            components_payload.get("textbox", {}),
            defaults.components.textbox,
        )
        components = BrandingComponents(
            table=table,
            chart=chart,
            image=image,
            textbox=textbox,
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
                            font=_parse_font_optional(
                                placement_data.get("font"), defaults.theme.body
                            ),
                            paragraph=_parse_paragraph_optional(placement_data.get("paragraph")),
                        )
                layouts[layout_name] = LayoutStyle(placements=placements)

        return cls(
            version=version,
            theme=theme,
            components=components,
            layouts=layouts,
        )

    @classmethod
    def default(cls) -> "BrandingConfig":
        heading = BrandingFont(name="Yu Gothic", size_pt=32.0, color_hex="#1A1A1A")
        body = BrandingFont(name="Yu Gothic", size_pt=18.0, color_hex="#333333")
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
                    name="Yu Gothic",
                    size_pt=18.0,
                    color_hex="#FFFFFF",
                    bold=True,
                ),
                fill_color="#005BAC",
            ),
            body=TableBodyStyle(
                font=BrandingFont(name="Yu Gothic", size_pt=16.0, color_hex="#333333"),
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
                font=BrandingFont(name="Yu Gothic", size_pt=14.0, color_hex="#333333")
            ),
        )
        image = ImageComponentStyle(
            fallback_box=BoxSpec(left_in=1.0, top_in=1.75, width_in=8.0, height_in=4.5),
            sizing="fit",
        )
        textbox = TextboxComponentStyle(
            fallback_box=BoxSpec(left_in=1.0, top_in=1.0, width_in=8.0, height_in=1.5),
            font=BrandingFont(name="Yu Gothic", size_pt=18.0, color_hex="#333333"),
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

    def resolve_fallback_box(
        self, element_type: str, *, layout: str | None = None, placement_key: str | None = None
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

    def resolve_layout_font(
        self, *, layout: str, placement_key: str, default: BrandingFont
    ) -> BrandingFont:
        if not placement_key:
            return default
        layout_style = self.layouts.get(layout)
        if not layout_style:
            return default
        placement = layout_style.placements.get(placement_key)
        return placement.font if placement and placement.font else default

    def resolve_layout_paragraph(
        self, *, layout: str, placement_key: str, default: ParagraphStyle
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
        color_hex=_ensure_hex_prefix(str(payload.get("color_hex", default.color_hex))),
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
        line_spacing_pt=_maybe_float(payload.get("line_spacing_pt", default.line_spacing_pt)),
        space_before_pt=_maybe_float(payload.get("space_before_pt", default.space_before_pt)),
        space_after_pt=_maybe_float(payload.get("space_after_pt", default.space_after_pt)),
        level=_maybe_int(payload.get("level", default.level)),
        left_indent_in=_maybe_float(payload.get("left_indent_in", default.left_indent_in)),
        right_indent_in=_maybe_float(payload.get("right_indent_in", default.right_indent_in)),
        first_line_indent_in=_maybe_float(payload.get("first_line_indent_in", default.first_line_indent_in)),
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


def _parse_table_component(
    payload: object, default: TableComponentStyle
) -> TableComponentStyle:
    if not isinstance(payload, dict):
        return default
    header_payload = payload.get("header", {})
    body_payload = payload.get("body", {})

    return TableComponentStyle(
        fallback_box=_parse_box(payload.get("fallback_box"), default.fallback_box),
        header=TableHeaderStyle(
            font=_parse_font(
                header_payload.get("font"),
                default.header.font,
            ),
            fill_color=_ensure_hex_prefix(
                header_payload.get("fill_color") or default.header.fill_color
            ),
        ),
        body=TableBodyStyle(
            font=_parse_font(body_payload.get("font"), default.body.font),
            fill_color=_ensure_hex_prefix(
                body_payload.get("fill_color") or default.body.fill_color
            ),
            zebra_fill_color=_resolve_optional_color(
                body_payload.get("zebra_fill_color"), default.body.zebra_fill_color
            ),
        ),
    )


def _parse_chart_component(
    payload: object, default: ChartComponentStyle
) -> ChartComponentStyle:
    if not isinstance(payload, dict):
        return default

    palette_payload = payload.get("palette")
    palette: tuple[str, ...]
    if isinstance(palette_payload, (list, tuple)) and palette_payload:
        palette = tuple(_ensure_hex_prefix(str(color)) for color in palette_payload)
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


def _parse_image_component(
    payload: object, default: ImageComponentStyle
) -> ImageComponentStyle:
    if not isinstance(payload, dict):
        return default

    fallback_box = _parse_box(payload.get("fallback_box"), default.fallback_box)
    sizing = str(payload.get("sizing", default.sizing)).lower()
    if sizing not in {"fit", "fill", "stretch"}:
        sizing = default.sizing

    return ImageComponentStyle(fallback_box=fallback_box, sizing=sizing)


def _parse_textbox_component(
    payload: object, default: TextboxComponentStyle
) -> TextboxComponentStyle:
    if not isinstance(payload, dict):
        return default

    fallback_box = _parse_box(payload.get("fallback_box"), default.fallback_box)
    font = _parse_font(payload.get("font"), default.font)
    paragraph = _parse_paragraph(payload.get("paragraph"), default.paragraph)

    return TextboxComponentStyle(
        fallback_box=fallback_box,
        font=font,
        paragraph=paragraph,
    )


def _resolve_optional_color(value: object, default: str | None) -> str | None:
    if value in (None, ""):
        return default
    return _ensure_hex_prefix(str(value))
