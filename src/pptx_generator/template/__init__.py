from __future__ import annotations

from pathlib import Path

from pptx_generator.models import TemplateStyle

from .branding_extractor import BrandingExtractionError, BrandingConfig, extract_branding_config

__all__ = [
    "BrandingConfig",
    "BrandingExtractionError",
    "extract_branding_config",
    "extract_template_style",
]


def extract_template_style(template_path: Path) -> tuple[TemplateStyle, dict[str, object]]:
    _ = template_path
    style = TemplateStyle.default()
    artifact = {"source": {"type": "default"}}
    return style, artifact
