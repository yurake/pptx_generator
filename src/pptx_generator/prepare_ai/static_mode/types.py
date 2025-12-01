"""静的モード関連の型定義。"""

from __future__ import annotations

from dataclasses import dataclass

from ...models import TemplateBlueprintSlide, TemplateBlueprintSlot


@dataclass(slots=True)
class StaticPromptOverride:
    slide_id: str
    slide_index: int
    instructions: str
    template_path: str | None = None


@dataclass(slots=True)
class StaticSlotEntry:
    order: int
    slide_index: int
    slide: TemplateBlueprintSlide
    slot: TemplateBlueprintSlot
