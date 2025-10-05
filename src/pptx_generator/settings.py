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
        return cls(
            max_title_length=title.get("max_length", cls.max_title_length),
            max_bullet_length=bullet.get("max_length", cls.max_bullet_length),
            max_bullet_level=bullet.get("max_level", cls.max_bullet_level),
            forbidden_words=tuple(data.get("forbidden_words", ())),
        )


@dataclass(slots=True)
class BrandingConfig:
    heading_font: str
    body_font: str
    body_font_size: float
    body_font_color: str
    primary_color: str
    background_color: str

    @classmethod
    def load(cls, path: Path) -> "BrandingConfig":
        data = json.loads(path.read_text(encoding="utf-8"))
        fonts = data.get("fonts", {})
        colors = data.get("colors", {})
        return cls(
            heading_font=fonts.get("heading", {}).get("name", "Yu Gothic"),
            body_font=fonts.get("body", {}).get("name", "Yu Gothic"),
            body_font_size=float(fonts.get("body", {}).get("size_pt", 18.0)),
            body_font_color=_ensure_hex_prefix(fonts.get("body", {}).get("color_hex", "#333333")),
            primary_color=_ensure_hex_prefix(colors.get("primary", "#005BAC")),
            background_color=_ensure_hex_prefix(colors.get("background", "#FFFFFF")),
        )


def _ensure_hex_prefix(value: str) -> str:
    return value if value.startswith("#") else f"#{value}"
