"""マッピング stage で利用する型定義。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from ...models import (
    ContentSlide,
    DraftSlideCard,
    GenerateReadySlide,
    MappingAIPatch,
    MappingFallbackState,
    MappingLogSlide,
    Slide,
)


@dataclass(slots=True)
class MappingOptions:
    """マッピング stage の設定。"""

    layouts_path: Path | None = None
    output_dir: Path | None = None
    generate_ready_filename: str = "generate_ready.json"
    mapping_log_filename: str = "mapping_log.json"
    fallback_report_filename: str | None = "fallback_report.json"
    max_candidates: int = 5
    template_path: Path | None = None


@dataclass(slots=True)
class LayoutProfile:
    """layouts.jsonl のレコード内容。"""

    layout_id: str
    layout_name: str
    usage_tags: tuple[str, ...]
    text_hint: Mapping[str, Any]
    media_hint: Mapping[str, Any]
    layout_description: dict[str, Any] | None = None
    placeholders: tuple[dict[str, Any], ...] = ()

    def allows_table(self) -> bool:
        return bool(self.media_hint.get("allow_table"))

    def max_lines(self) -> int | None:
        value = self.text_hint.get("max_lines")
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None


@dataclass(slots=True)
class MappingWorkItem:
    """マッピング処理対象の入力一式。"""

    page_no: int
    section_name: str | None
    spec_slide: Slide | None
    card: DraftSlideCard | None
    content_slide: ContentSlide | None


@dataclass(slots=True)
class MappingAccumulator:
    """マッピング処理中に蓄積する生成結果・統計。"""

    generate_ready_slides: list[GenerateReadySlide] = field(default_factory=list)
    log_slides: list[MappingLogSlide] = field(default_factory=list)
    fallback_records: list[dict[str, Any]] = field(default_factory=list)
    fallback_slide_ids: set[str] = field(default_factory=set)
    ai_patch_count: int = 0
    ai_patch_slide_ids: set[str] = field(default_factory=set)

    def register_fallback(
        self,
        *,
        slide_id: str,
        fallback_state: MappingFallbackState,
    ) -> None:
        if not fallback_state.applied:
            return
        self.fallback_slide_ids.add(slide_id)
        self.fallback_records.append(
            {
                "slide_id": slide_id,
                "history": list(fallback_state.history),
                "reason": fallback_state.reason,
            }
        )

    def register_ai_patches(self, *, slide_id: str, patches: Sequence[MappingAIPatch]) -> None:
        if not patches:
            return
        self.ai_patch_count += len(patches)
        self.ai_patch_slide_ids.add(slide_id)
