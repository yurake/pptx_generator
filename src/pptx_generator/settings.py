"""設定ファイルの読み込みユーティリティ。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RulesConfig:
    max_title_length: int = 25
    max_bullet_length: int = 120
    max_bullet_level: int = 3
    forbidden_words: tuple[str, ...] = ()

    @classmethod
    def load(cls, path: Path) -> "RulesConfig":
        data = json.loads(path.read_text(encoding="utf-8"))
        title = data.get("title", {})
        bullet = data.get("bullet", {})
        defaults = cls()
        return cls(
            max_title_length=title.get("max_length", defaults.max_title_length),
            max_bullet_length=bullet.get("max_length", defaults.max_bullet_length),
            max_bullet_level=bullet.get("max_level", defaults.max_bullet_level),
            forbidden_words=tuple(data.get("forbidden_words", defaults.forbidden_words)),
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


def _ensure_hex_prefix(value: str) -> str:
    return value if value.startswith("#") else f"#{value}"
