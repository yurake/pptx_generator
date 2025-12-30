from __future__ import annotations

from pptx_generator.settings.branding import BrandingConfig, DEFAULT_FONT_FAMILY


def test_branding_config_default_fonts_use_shared_family():
    config = BrandingConfig.default()

    assert config.heading_font.name == DEFAULT_FONT_FAMILY
    assert config.body_font.name == DEFAULT_FONT_FAMILY
    assert config.components.table.header.font.name == DEFAULT_FONT_FAMILY
    assert config.components.table.body.font.name == DEFAULT_FONT_FAMILY
    assert config.components.chart.axis.font.name == DEFAULT_FONT_FAMILY
    assert config.components.textbox.font.name == DEFAULT_FONT_FAMILY
