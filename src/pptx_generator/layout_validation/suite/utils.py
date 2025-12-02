"""レイアウト検証スイートのユーティリティ関数。"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Dict

from ...models import LayoutInfo


def resolve_layout_id(layout: LayoutInfo, seen: Dict[str, int]) -> str:
    if layout.identifier:
        base = f"id_{layout.identifier}"
    else:
        base = slugify_layout_name(layout.name)
    if not base:
        base = "layout"
    count = seen.get(base, 0) + 1
    seen[base] = count
    if count == 1:
        return base
    return f"{base}__{count:02d}"


def slugify_layout_name(name: str) -> str:
    normalised = unicodedata.normalize("NFKC", name or "").strip()
    normalised = normalised.replace(" ", "_")
    normalised = re.sub(r"[\s/\\]+", "_", normalised)
    normalised = re.sub(r"[^0-9A-Za-z_\-一-龯ぁ-んァ-ンー]+", "", normalised)
    return normalised.lower()


def derive_template_id(path: Path) -> str:
    stem = unicodedata.normalize("NFKC", path.stem)
    stem = re.sub(r"[^0-9A-Za-z_\-一-龯ぁ-んァ-ンー]+", "", stem)
    return stem or "template"
