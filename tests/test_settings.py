"""RulesConfig と BrandingConfig の読み込みテスト。"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from pptx_generator.settings import BrandingConfig, RulesConfig


def write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


class TestRulesConfig:
    def test_load_with_custom_values(self, tmp_path: Path) -> None:
        config_path = write_json(
            tmp_path / "rules.json",
            {
                "title": {"max_length": 10},
                "bullet": {"max_length": 90, "max_level": 2},
                "forbidden_words": ["NG", "禁止"],
            },
        )

        config = RulesConfig.load(config_path)

        assert config.max_title_length == 10
        assert config.max_bullet_length == 90
        assert config.max_bullet_level == 2
        assert config.forbidden_words == ("NG", "禁止")

    def test_load_fallback_to_defaults(self, tmp_path: Path) -> None:
        config_path = write_json(tmp_path / "rules.json", {})

        config = RulesConfig.load(config_path)

        assert config.max_title_length == RulesConfig().max_title_length
        assert config.max_bullet_length == RulesConfig().max_bullet_length
        assert config.max_bullet_level == RulesConfig().max_bullet_level
        assert config.forbidden_words == ()

    def test_load_invalid_json_raises(self, tmp_path: Path) -> None:
        config_path = tmp_path / "broken.json"
        config_path.write_text("{ invalid json", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            RulesConfig.load(config_path)


class TestBrandingConfig:
    def test_load_with_complete_data(self, tmp_path: Path) -> None:
        config_path = write_json(
            tmp_path / "branding.json",
            {
                "fonts": {
                    "heading": {"name": "Heading", "size_pt": 30, "color_hex": "#111111"},
                    "body": {"name": "Body", "size_pt": 16, "color_hex": "0F0F0F"},
                },
                "colors": {
                    "primary": "112233",
                    "background": "FFFFFF",
                },
            },
        )

        config = BrandingConfig.load(config_path)

        assert config.heading_font.name == "Heading"
        assert config.heading_font.size_pt == pytest.approx(30.0)
        assert config.heading_font.color_hex == "#111111"
        assert config.body_font.name == "Body"
        assert config.body_font.size_pt == pytest.approx(16.0)
        assert config.body_font.color_hex == "#0F0F0F"
        assert config.primary_color == "#112233"
        assert config.secondary_color == "#0097A7"
        assert config.accent_color == "#FF7043"
        assert config.background_color == "#FFFFFF"

    def test_load_fallback_for_missing_body_font(self, tmp_path: Path) -> None:
        config_path = write_json(
            tmp_path / "branding.json",
            {
                "fonts": {
                    "heading": {"name": "Heading"},
                },
                "colors": {},
            },
        )

        config = BrandingConfig.load(config_path)

        assert config.body_font.name == "Yu Gothic"
        assert config.body_font.size_pt == pytest.approx(18.0)
        assert config.body_font.color_hex == "#333333"

    def test_load_invalid_json_raises(self, tmp_path: Path) -> None:
        config_path = tmp_path / "branding.json"
        config_path.write_text(textwrap.dedent(
            """
            {
              "fonts": {
            """
        ).strip(), encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            BrandingConfig.load(config_path)
