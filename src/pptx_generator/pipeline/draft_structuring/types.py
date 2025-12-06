from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...models import ContentSlide, DraftDocument, DraftSection, GenerateReadyDocument, Slide
from ...prepare.models import PrepareCard


@dataclass(slots=True)
class DraftStructuringOptions:
    """ドラフト構成ステップの設定。"""

    layouts_path: Path | None = None
    output_dir: Path | None = None
    spec_source_path: Path | None = None
    draft_filename: str = "draft_draft.json"
    approved_filename: str = "draft_approved.json"
    log_filename: str = "draft_review_log.json"
    generate_ready_filename: str = "generate_ready.json"
    generate_ready_meta_filename: str = "generate_ready_meta.json"
    mapping_log_filename: str = "draft_mapping_log.json"
    target_length: int | None = None
    structure_pattern: str | None = None
    appendix_limit: int = 5
    analysis_summary_path: Path | None = None
    enable_ai_recommender: bool = True
    ai_weight: float = 0.25
    diversity_weight: float = 0.05
    max_layout_candidates: int = 5
    layout_ai_policy_path: Path | None = Path("config/layout_ai_policies.json")
    layout_ai_policy_id: str | None = "layout-default"
    enable_ai_simulation: bool = True
    enable_slide_alignment: bool = True
    slide_alignment_threshold: float = 0.6
    slide_alignment_max_candidates: int = 12


@dataclass(slots=True)
class DraftWorkItem:
    """ドラフト構築処理対象の入力一式。"""

    content_slide: ContentSlide | None
    spec_slide: Slide | None


@dataclass(slots=True)
class DraftAccumulator:
    """ドラフト構築中に蓄積する生成結果・統計。"""

    sections: list[DraftSection] = field(default_factory=list)
    section_map: dict[str, DraftSection] = field(default_factory=dict)
    mapping_logs: list[dict[str, Any]] = field(default_factory=list)
    ai_summary: dict[str, Any] = field(
        default_factory=lambda: {
            "invoked": 0,
            "used": 0,
            "simulated": 0,
            "models": {},
        }
    )


@dataclass(slots=True)
class StaticArtifacts:
    draft: DraftDocument
    generate_ready: GenerateReadyDocument
    mapping_log: dict[str, Any]
    ai_summary: dict[str, Any]
    slot_summary: dict[str, int]


def card_slot_id(card: PrepareCard) -> str | None:
    blueprint = card.blueprint_meta()
    if not blueprint:
        return None
    slot_id = blueprint.get("slot_id")
    return str(slot_id) if slot_id else None


def card_slot_fulfilled(card: PrepareCard | None) -> bool:
    if card is None:
        return False
    blueprint = card.blueprint_meta()
    if not blueprint:
        return False
    return bool(blueprint.get("fulfilled"))


__all__ = [
    "DraftStructuringOptions",
    "DraftWorkItem",
    "DraftAccumulator",
    "StaticArtifacts",
    "card_slot_id",
    "card_slot_fulfilled",
]
