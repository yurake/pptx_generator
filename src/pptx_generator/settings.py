"""設定ファイルの読み込みユーティリティ。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


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
class RulesConfig:
    max_title_length: int = 25
    max_bullet_length: int = 120
    max_bullet_level: int = 3
    forbidden_words: tuple[str, ...] = ()
    analyzer: AnalyzerRuleConfig = field(default_factory=AnalyzerRuleConfig)
    refiner: RefinerRuleConfig = field(default_factory=RefinerRuleConfig)

    @classmethod
    def load(cls, path: Path) -> "RulesConfig":
        data = json.loads(path.read_text(encoding="utf-8"))
        title = data.get("title", {})
        bullet = data.get("bullet", {})
        defaults = cls()
        analyzer = AnalyzerRuleConfig.from_dict(data.get("analyzer", {}))
        refiner = RefinerRuleConfig.from_dict(data.get("refiner", {}))
        return cls(
            max_title_length=title.get("max_length", defaults.max_title_length),
            max_bullet_length=bullet.get("max_length", defaults.max_bullet_length),
            max_bullet_level=bullet.get("max_level", defaults.max_bullet_level),
            forbidden_words=tuple(data.get("forbidden_words", defaults.forbidden_words)),
            analyzer=analyzer,
            refiner=refiner,
        )


@dataclass(slots=True)
class BrandingFont:
    name: str
    size_pt: float
    color_hex: str


@dataclass(slots=True)
class BrandingConfig:
    heading_font: BrandingFont
    body_font: BrandingFont
    primary_color: str
    secondary_color: str
    accent_color: str
    background_color: str

    @classmethod
    def load(cls, path: Path) -> "BrandingConfig":
        data = json.loads(path.read_text(encoding="utf-8"))
        defaults = cls.default()
        fonts = data.get("fonts", {})
        colors = data.get("colors", {})

        heading_settings = fonts.get("heading", {})
        body_settings = fonts.get("body", {})

        heading_font = BrandingFont(
            name=heading_settings.get("name") or defaults.heading_font.name,
            size_pt=float(heading_settings.get("size_pt") or defaults.heading_font.size_pt),
            color_hex=_ensure_hex_prefix(
                heading_settings.get("color_hex") or defaults.heading_font.color_hex
            ),
        )
        body_font = BrandingFont(
            name=body_settings.get("name") or defaults.body_font.name,
            size_pt=float(body_settings.get("size_pt") or defaults.body_font.size_pt),
            color_hex=_ensure_hex_prefix(
                body_settings.get("color_hex") or defaults.body_font.color_hex
            ),
        )

        return cls(
            heading_font=heading_font,
            body_font=body_font,
            primary_color=_ensure_hex_prefix(colors.get("primary") or defaults.primary_color),
            secondary_color=_ensure_hex_prefix(
                colors.get("secondary") or defaults.secondary_color
            ),
            accent_color=_ensure_hex_prefix(colors.get("accent") or defaults.accent_color),
            background_color=_ensure_hex_prefix(
                colors.get("background") or defaults.background_color
            ),
        )

    @classmethod
    def default(cls) -> "BrandingConfig":
        return cls(
            heading_font=BrandingFont(name="Yu Gothic", size_pt=32.0, color_hex="#1A1A1A"),
            body_font=BrandingFont(name="Yu Gothic", size_pt=18.0, color_hex="#333333"),
            primary_color="#005BAC",
            secondary_color="#0097A7",
            accent_color="#FF7043",
            background_color="#FFFFFF",
        )
