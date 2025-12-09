"""Template extractor options."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

__all__ = ["TemplateExtractorOptions"]


@dataclass
class TemplateExtractorOptions:
    """TemplateExtractor の設定オプション。"""

    template_path: Path
    output_path: Optional[Path] = None
    layout_filter: Optional[str] = None
    anchor_filter: Optional[str] = None
    format: str = "json"  # json または yaml
    layout_mode: str = "dynamic"
    static_source: Literal["slide", "template"] = "template"
