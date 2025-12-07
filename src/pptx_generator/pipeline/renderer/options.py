from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ...models import TemplateStyle


@dataclass(slots=True)
class RenderingOptions:
    template_path: Path | None = None
    output_filename: str = "proposal.pptx"
    template_style: TemplateStyle | None = None
    template_source: Literal["slide", "template"] = "template"
    prototype_mapping: list[int] | None = None
