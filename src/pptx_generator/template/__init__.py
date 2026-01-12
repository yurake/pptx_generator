"""テンプレート関連のユーティリティ集。"""

from __future__ import annotations

from .branding_extractor import (
    BrandingExtractionError,
    BrandingExtractionResult,
    SCHEME_COLOR_TAG,
    extract_branding_config,
)
from .spec_loader import convert_scaffold_to_jobspec, load_jobspec_from_path
from .template_style import extract_template_style, template_style_from_branding

__all__ = [
    "BrandingExtractionError",
    "BrandingExtractionResult",
    "SCHEME_COLOR_TAG",
    "convert_scaffold_to_jobspec",
    "extract_branding_config",
    "extract_template_style",
    "load_jobspec_from_path",
    "template_style_from_branding",
]
