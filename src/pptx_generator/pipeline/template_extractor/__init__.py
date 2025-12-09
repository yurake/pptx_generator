"""Template extractor package."""

from __future__ import annotations

from pptx import Presentation

from .constants import (
    AUTO_DRAW_PLACEHOLDER_TYPES,
    EMU_PER_INCH,
    JOBSPEC_SCHEMA_VERSION,
    MAX_SAMPLE_TEXT_LENGTH,
    SLIDE_BULLET_ANCHORS,
)
from .errors import DuplicateAnchorError
from .extractor import TemplateExtractor
from .options import TemplateExtractorOptions
from .step import TemplateExtractorStep

__all__ = [
    "TemplateExtractor",
    "TemplateExtractorOptions",
    "TemplateExtractorStep",
    "DuplicateAnchorError",
    "Presentation",
    "SLIDE_BULLET_ANCHORS",
    "JOBSPEC_SCHEMA_VERSION",
    "MAX_SAMPLE_TEXT_LENGTH",
    "EMU_PER_INCH",
    "AUTO_DRAW_PLACEHOLDER_TYPES",
]
