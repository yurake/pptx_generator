"""JobSpec scaffold builder mixin."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from .constants import (
    AUTO_DRAW_PLACEHOLDER_TYPES,
    JOBSPEC_SCHEMA_VERSION,
    MAX_SAMPLE_TEXT_LENGTH,
)
from .helpers import derive_template_id, slugify_layout_name

if TYPE_CHECKING:
    from ...models import (
        JobSpecScaffold,
        JobSpecScaffoldSlide,
        LayoutInfo,
        ShapeInfo,
        TemplateSpec,
    )

__all__ = ["JobSpecBuilderMixin"]


class JobSpecBuilderMixin:
    """Provides helpers to build JobSpec scaffolds."""

    options: object

    def build_jobspec_scaffold(
        self,
        template_spec: "TemplateSpec",
        template_spec_path: Path | str | None = None,
    ) -> "JobSpecScaffold":
        from ...models import (
            JobSpecScaffold,
            JobSpecScaffoldBounds,
            JobSpecScaffoldMeta,
            JobSpecScaffoldPlaceholder,
            JobSpecScaffoldSlide,
        )

        template_path = self.options.template_path
        template_id = derive_template_id(template_path)
        meta = JobSpecScaffoldMeta(
            schema_version=JOBSPEC_SCHEMA_VERSION,
            template_path=str(template_path),
            template_id=template_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            layout_count=len(template_spec.layouts),
            template_spec_path=str(template_spec_path) if template_spec_path else None,
            template_source=template_spec.template_source,
        )

        counters: defaultdict[str, int] = defaultdict(int)
        slides: list[JobSpecScaffoldSlide] = []

        for layout in template_spec.layouts:
            counters[layout.name] += 1
            sequence = counters[layout.name]
            slide_id = self._resolve_slide_id(layout, sequence)

            placeholders: list[JobSpecScaffoldPlaceholder] = []
            for index, anchor in enumerate(layout.anchors, start=1):
                anchor_name = anchor.name or f"shape_{index:02d}"
                placeholder_type = (anchor.placeholder_type or "").upper()
                is_auto_draw = placeholder_type in AUTO_DRAW_PLACEHOLDER_TYPES

                bounds = JobSpecScaffoldBounds(
                    left_in=anchor.left_in,
                    top_in=anchor.top_in,
                    width_in=anchor.width_in,
                    height_in=anchor.height_in,
                )
                placeholder = JobSpecScaffoldPlaceholder(
                    anchor=anchor_name,
                    kind=self._infer_placeholder_kind(anchor),
                    placeholder_type=anchor.placeholder_type,
                    shape_type=anchor.shape_type,
                    is_placeholder=anchor.is_placeholder,
                    bounds=bounds,
                    sample_text=self._sanitize_sample_text(anchor.text),
                    notes=self._collect_placeholder_notes(anchor),
                    auto_draw=is_auto_draw,
                    font=anchor.font,
                    paragraph=anchor.paragraph,
                    text_frame_padding=anchor.text_frame_padding,
                    text_capacity=anchor.text_capacity,
                )
                placeholders.append(placeholder)

            slides.append(
                JobSpecScaffoldSlide(
                    id=slide_id,
                    layout=layout.name,
                    sequence=sequence,
                    placeholders=placeholders,
                )
            )

        return JobSpecScaffold(meta=meta, slides=slides)

    def _resolve_slide_id(self, layout: "LayoutInfo", sequence: int) -> str:
        base = None
        if layout.identifier:
            base = f"id_{layout.identifier}"
        if not base:
            base = slugify_layout_name(layout.name)
        if not base:
            base = "slide"
        suffix = f"{sequence:02d}"
        return f"{base}-{suffix}"

    @staticmethod
    def _sanitize_sample_text(text: str | None) -> str | None:
        if text is None:
            return None
        cleaned_lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not cleaned_lines:
            cleaned = text.strip()
            if not cleaned:
                return None
        else:
            cleaned = "\n".join(cleaned_lines)
        if len(cleaned) > MAX_SAMPLE_TEXT_LENGTH:
            return cleaned[:MAX_SAMPLE_TEXT_LENGTH].rstrip() + "..."
        return cleaned

    @staticmethod
    def _collect_placeholder_notes(shape: "ShapeInfo") -> list[str]:
        notes: list[str] = []
        if shape.conflict:
            notes.append(shape.conflict)
        if shape.missing_fields:
            notes.append("missing_fields: " + ", ".join(shape.missing_fields))
        if shape.error:
            notes.append(shape.error)
        if shape.width_in <= 0 or shape.height_in <= 0:
            notes.append("size_not_positive")
        return notes
