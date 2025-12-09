"""Blueprint building mixin."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .constants import AUTO_DRAW_PLACEHOLDER_TYPES

if TYPE_CHECKING:
    from ...models import (
        LayoutInfo,
        ShapeInfo,
        TemplateBlueprint,
        TemplateBlueprintSlide,
        TemplateBlueprintSlot,
    )


logger = logging.getLogger(__name__)

__all__ = ["BlueprintBuilderMixin"]


class BlueprintBuilderMixin:
    """Provides blueprint building helpers."""

    def _build_blueprint(self, layouts: list["LayoutInfo"]) -> "TemplateBlueprint":
        from ...models import (
            TemplateBlueprint,
            TemplateBlueprintSlide,
            TemplateBlueprintSlot,
        )

        slides: list[TemplateBlueprintSlide] = []

        for index, layout in enumerate(layouts, start=1):
            slide_id = self._resolve_slide_id(layout, index)
            slot_sequence = 1
            slots: list[TemplateBlueprintSlot] = []
            for anchor in layout.anchors:
                placeholder_type = (anchor.placeholder_type or "").upper()
                if placeholder_type in AUTO_DRAW_PLACEHOLDER_TYPES:
                    logger.debug(
                        "Blueprint から自動描画プレースホルダーを除外: slide=%s anchor=%s type=%s",
                        slide_id,
                        anchor.name,
                        placeholder_type,
                    )
                    continue
                content_type = self._infer_placeholder_kind(anchor)
                slot_id = f"{slide_id}.slot{slot_sequence:02d}"
                slot_sequence += 1
                required = self._is_required_slot(anchor)
                default_text: list[str] | None = None
                default_payload: dict[str, Any] | None = None
                if content_type == "text":
                    source_text = anchor.text or ""
                    lines = [
                        line.strip()
                        for line in source_text.splitlines()
                        if line.strip()
                    ]
                    if lines:
                        default_text = lines
                slots.append(
                    TemplateBlueprintSlot(
                        slot_id=slot_id,
                        anchor=anchor.name,
                        content_type=content_type,
                        required=required,
                        intent_tags=self._derive_slot_intent_tags(anchor, layout.name),
                        default_text=default_text,
                        default_payload=default_payload,
                    )
                )

            slides.append(
                TemplateBlueprintSlide(
                    slide_id=slide_id,
                    layout=layout.name,
                    prototype_index=layout.prototype_index,
                    required=True,
                    intent_tags=self._derive_layout_intent_tags(layout.name),
                    slots=slots,
                )
            )

        return TemplateBlueprint(slides=slides)

    def _infer_placeholder_kind(self, shape: "ShapeInfo") -> str:
        placeholder_type = (shape.placeholder_type or "").upper()
        if placeholder_type in {
            "TITLE",
            "CENTER_TITLE",
            "SUBTITLE",
            "BODY",
            "CONTENT",
            "TEXT",
        }:
            return "text"
        if placeholder_type in {"PICTURE", "CLIP_ART", "BITMAP", "OBJECT"}:
            return "image"
        if placeholder_type in {"TABLE"}:
            return "table"
        if placeholder_type in {"CHART"}:
            return "chart"

        shape_type = (shape.shape_type or "").lower()
        if "chart" in shape_type or "graph" in shape_type:
            return "chart"
        if "table" in shape_type:
            return "table"
        if "picture" in shape_type or "image" in shape_type or "bitmap" in shape_type:
            return "image"
        if shape.text:
            return "text"
        return "other"

    def _is_required_slot(self, shape: "ShapeInfo") -> bool:
        placeholder_type = (shape.placeholder_type or "").upper()
        if placeholder_type in {"TITLE", "CENTER_TITLE", "BODY"}:
            return True
        if placeholder_type in {"SUBTITLE", "CONTENT"}:
            return False
        shape_type = (shape.shape_type or "").lower()
        if "picture" in shape_type or "image" in shape_type:
            return False
        if "chart" in shape_type or "table" in shape_type:
            return False
        return True

    @staticmethod
    def _derive_slot_intent_tags(
        shape: "ShapeInfo", layout_name: str | None
    ) -> list[str]:
        del layout_name  # 現状は形状からの推測に限定
        placeholder_type = (shape.placeholder_type or "").upper()
        if placeholder_type in {"TITLE", "CENTER_TITLE"}:
            return ["headline"]
        if placeholder_type in {"SUBTITLE"}:
            return ["subheadline"]
        if placeholder_type in {"BODY", "CONTENT", "TEXT"}:
            return ["body"]
        return []

    @staticmethod
    def _derive_layout_intent_tags(layout_name: str | None) -> list[str]:
        name = (layout_name or "").lower()
        if "title" in name or "cover" in name:
            return ["opening"]
        if "closing" in name:
            return ["closing"]
        if "agenda" in name:
            return ["agenda"]
        if "summary" in name:
            return ["summary"]
        return []
