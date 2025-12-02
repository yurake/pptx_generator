"""Settings package with modular configuration helpers."""

from __future__ import annotations

from .branding import (
    BrandingConfig,
    BrandingComponents,
    BrandingFont,
    BrandingTheme,
    BoxSpec,
    ChartAxisStyle,
    ChartComponentStyle,
    ChartDataLabelsStyle,
    ColorPalette,
    ImageComponentStyle,
    LayoutStyle,
    ParagraphStyle,
    PlacementStyle,
    TableBodyStyle,
    TableComponentStyle,
    TableHeaderStyle,
    TextboxComponentStyle,
)
from .loader import load_branding_config, load_rules_config
from .rules import AnalyzerRuleConfig, PolisherRuleConfig, RefinerRuleConfig, RulesConfig

__all__ = [
    "AnalyzerRuleConfig",
    "PolisherRuleConfig",
    "RefinerRuleConfig",
    "RulesConfig",
    "BrandingConfig",
    "BrandingComponents",
    "BrandingFont",
    "BrandingTheme",
    "ColorPalette",
    "ChartAxisStyle",
    "ChartComponentStyle",
    "ChartDataLabelsStyle",
    "BoxSpec",
    "ImageComponentStyle",
    "TableBodyStyle",
    "TableComponentStyle",
    "TableHeaderStyle",
    "TextboxComponentStyle",
    "ParagraphStyle",
    "PlacementStyle",
    "LayoutStyle",
    "load_rules_config",
    "load_branding_config",
]
