from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class BrandingExtractionError(RuntimeError):
    pass


@dataclass(frozen=True)
class BrandingConfig:
    fonts: dict[str, dict[str, Any]] | None = None

    def to_branding_payload(self) -> dict[str, Any]:
        return {"fonts": self.fonts or {}}


def extract_branding_config(template_path: Path) -> BrandingConfig:
    _ = template_path
    return BrandingConfig(fonts=None)
