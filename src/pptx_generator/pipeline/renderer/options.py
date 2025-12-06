from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...models import TemplateStyle


@dataclass(slots=True)
class RenderingOptions:
    template_path: Path | None = None
    output_filename: str = "proposal.pptx"
    template_style: TemplateStyle | None = None
