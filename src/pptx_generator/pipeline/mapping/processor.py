"""スライド単位のマッピング処理。"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Sequence

from ...models import (
    ContentSlide,
    DraftSlideCard,
    GenerateReadySlide,
    JsonPatchOperation,
    MappingAIPatch,
    MappingLogCapacityWarning,
    MappingCandidate,
    MappingFallbackState,
    MappingLogSlide,
    MappingSlideMeta,
    Slide,
)
from ...prepare.models import PrepareCard
from ..draft_structuring.slide_elements import build_body_blocks
from ..table_anchor import build_table_payload, is_table_payload, resolve_table_anchor
from ...utils.usage_tags import normalize_usage_tag_value
from ...utils.text_lines import split_lines_preserve_blank
from .llm_fit import (
    MappingTextFitClient,
    MappingTextFitClientExecutionError,
    MappingTextFitResponseFormatError,
    MappingTextFitRequest,
)
from .types import LayoutProfile, MappingAccumulator, MappingOptions, MappingWorkItem

logger = logging.getLogger(__name__)


class MappingSlideProcessor:
    """MappingStep のスライド処理ロジック。"""

    def __init__(
        self,
        *,
        options: MappingOptions,
        layout_catalog: Mapping[str, LayoutProfile],
        prepare_lookup: Mapping[str, PrepareCard] | None = None,
        text_fit_client: MappingTextFitClient | None = None,
        text_fit_error: str | None = None,
    ) -> None:
        self.options = options
        self.layout_catalog = layout_catalog
        self.prepare_lookup = prepare_lookup
        self.text_fit_client = text_fit_client
        self.text_fit_error = text_fit_error

    def process(
        self,
        *,
        item: MappingWorkItem,
        accumulator: MappingAccumulator,
        previous_layout: str | None,
    ) -> str | None:
        slide_id = self._resolve_slide_id(item)

        candidates = self._score_candidates(
            slide_id=slide_id,
            content_slide=item.content_slide,
            previous_layout=previous_layout,
        )
        if item.card and item.card.layout_candidates:
            candidates = self._merge_layout_candidates(
                candidates, item.card.layout_candidates
            )

        default_layout = self._resolve_default_layout(item)
        selected_layout = self._select_layout(default_layout, item.card, candidates)
        selected_profile = self.layout_catalog.get(selected_layout)

        prepare_card = None
        if self.prepare_lookup and item.content_slide and item.content_slide.source:
            source_id = item.content_slide.source.card_id
            if source_id:
                prepare_card = self.prepare_lookup.get(source_id)
        if prepare_card is None and self.prepare_lookup and item.card:
            prepare_card = self.prepare_lookup.get(item.card.ref_id)

        elements = self._build_elements(item.spec_slide, item.content_slide, prepare_card)
        if item.content_slide and item.content_slide.elements:
            table_payload = self._build_table_payload(
                item=item,
                selected_profile=selected_profile,
                selected_layout=selected_layout,
            )
            if table_payload is not None:
                elements = self._merge_table_payload(
                    elements=elements,
                    payload=table_payload,
                )

        fallback_state, ai_patches, warnings, capacity_warnings = self._apply_capacity_controls(
            slide_id=slide_id,
            layout=selected_profile,
            elements=elements,
        )
        accumulator.register_fallback(slide_id=slide_id, fallback_state=fallback_state)
        accumulator.register_ai_patches(slide_id=slide_id, patches=ai_patches)

        sources = [slide_id] if item.spec_slide is None else [item.spec_slide.id]
        layout_name = selected_profile.layout_name if selected_profile else selected_layout
        layout_description = (
            selected_profile.layout_description if selected_profile else None
        )
        auto_draw_payload = self._build_auto_draw_payload(item.spec_slide)
        fallback_marker = (
            fallback_state.history[-1]
            if fallback_state.applied and fallback_state.history
            else "none"
        )

        accumulator.generate_ready_slides.append(
            GenerateReadySlide(
                layout_id=selected_layout,
                layout_name=layout_name,
                elements=elements,
                meta=MappingSlideMeta(
                    section=item.section_name,
                    page_no=item.page_no,
                    sources=sources,
                    fallback=fallback_marker,
                    layout_description=layout_description,
                    auto_draw=auto_draw_payload,
                ),
            )
        )

        accumulator.log_slides.append(
            MappingLogSlide(
                ref_id=slide_id,
                selected_layout=selected_layout,
                candidates=candidates[: self.options.max_candidates],
                fallback=fallback_state,
                ai_patch=ai_patches,
                warnings=warnings,
                capacity_warnings=capacity_warnings,
                layout_description=layout_description,
            )
        )

        return selected_layout

    def _resolve_slide_id(self, item: MappingWorkItem) -> str:
        if item.spec_slide is not None:
            return item.spec_slide.id
        if item.card is not None:
            return item.card.ref_id
        return f"page-{item.page_no}"

    def _score_candidates(
        self,
        *,
        slide_id: str,
        content_slide: ContentSlide | None,
        previous_layout: str | None,
    ) -> list[MappingCandidate]:
        intent = normalize_usage_tag_value(content_slide.intent if content_slide else None)
        if intent is None:
            intent = (content_slide.intent or "").casefold() if content_slide else ""

        type_hint = normalize_usage_tag_value(
            content_slide.type_hint if content_slide else None
        )
        if type_hint is None:
            type_hint = (
                (content_slide.type_hint or "").casefold() if content_slide else ""
            )

        source_tags: set[str] = set()
        if content_slide and content_slide.source and content_slide.source.intent_tags:
            for tag in content_slide.source.intent_tags:
                normalized = normalize_usage_tag_value(tag)
                if normalized:
                    source_tags.add(normalized)
        if intent:
            source_tags.add(intent)
        if type_hint:
            source_tags.add(type_hint)

        body_lines = (
            len(content_slide.elements.body)
            if content_slide and content_slide.elements and content_slide.elements.body
            else 0
        )
        has_table = (
            bool(content_slide.elements.table_data)
            if content_slide and content_slide.elements
            else False
        )

        candidates: list[MappingCandidate] = []
        seen_layout_ids: set[str] = set()
        for profile in self.layout_catalog.values():
            if profile.layout_id in seen_layout_ids:
                continue
            seen_layout_ids.add(profile.layout_id)
            score = 0.0
            if intent and intent in profile.usage_tags:
                score += 0.5
            if type_hint and type_hint in profile.usage_tags:
                score += 0.15
            if source_tags and any(tag in profile.usage_tags for tag in source_tags):
                score += 0.1
            max_lines = profile.max_lines()
            if max_lines is not None:
                if body_lines <= max_lines:
                    score += 0.3
                else:
                    score -= min(0.3, (body_lines - max_lines) * 0.05)
            elif body_lines <= 6:
                score += 0.1
            if has_table:
                score += 0.05 if profile.allows_table() else -0.2
            if previous_layout and profile.layout_id == previous_layout:
                score -= 0.05

            clamped = max(0.0, min(1.0, round(score, 3)))
            if clamped <= 0.0:
                continue
            candidates.append(MappingCandidate(layout_id=profile.layout_id, score=clamped))

        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        return candidates[: self.options.max_candidates]

    def _merge_layout_candidates(
        self,
        scorer_candidates: Sequence[MappingCandidate],
        card_candidates: Sequence[MappingCandidate],
    ) -> list[MappingCandidate]:
        merged = {candidate.layout_id: candidate.score for candidate in scorer_candidates}
        for candidate in card_candidates:
            existing_score = merged.get(candidate.layout_id)
            if existing_score is None:
                merged[candidate.layout_id] = candidate.score
                continue
            merged[candidate.layout_id] = max(existing_score, candidate.score)
        result = [
            MappingCandidate(layout_id=layout_id, score=score)
            for layout_id, score in merged.items()
        ]
        result.sort(key=lambda candidate: candidate.score, reverse=True)
        return result[: self.options.max_candidates]

    def _resolve_default_layout(self, item: MappingWorkItem) -> str:
        if item.spec_slide is not None:
            return item.spec_slide.layout or "title"
        if item.card is not None:
            return item.card.layout_hint or "title"
        return "title"

    @staticmethod
    def _select_layout(
        default_layout: str,
        card: DraftSlideCard | None,
        candidates: Sequence[MappingCandidate],
    ) -> str:
        if card and card.layout_hint:
            return card.layout_hint
        if candidates:
            return candidates[0].layout_id
        return default_layout

    def _build_elements(
        self,
        spec_slide: Slide | None,
        content_slide: ContentSlide | None,
        prepare_card: PrepareCard | None,
    ) -> dict[str, Any]:
        if content_slide is not None and content_slide.elements is not None:
            base = self._build_elements(spec_slide, None, None)
            elements: dict[str, Any] = {
                "title": content_slide.elements.title,
            }
            if content_slide.elements.subtitle:
                elements["subtitle"] = content_slide.elements.subtitle
            elif "subtitle" in base:
                elements["subtitle"] = base["subtitle"]
            if content_slide.elements.body:
                elements["body"] = list(content_slide.elements.body)
            elif "body" in base:
                elements["body"] = base["body"]
            if prepare_card is not None:
                structured_blocks, has_non_bullet, has_bullets, has_custom = (
                    build_body_blocks(prepare_card)
                )
                if structured_blocks and (has_custom or (has_non_bullet and has_bullets)):
                    elements["body"] = structured_blocks
            if content_slide.elements.note:
                elements["note"] = content_slide.elements.note
            elif "note" in base:
                elements["note"] = base["note"]
            if content_slide.elements.table_data is not None:
                elements["table"] = {
                    "headers": list(content_slide.elements.table_data.headers),
                    "rows": [
                        list(row) for row in content_slide.elements.table_data.rows
                    ],
                }
            if spec_slide is not None and spec_slide.subtitle and "subtitle" not in elements:
                elements["subtitle"] = spec_slide.subtitle
            for key, value in base.items():
                if key in {"title", "body", "note", "subtitle"}:
                    continue
                elements.setdefault(key, value)
            return elements

        if spec_slide is None:
            return {}

        elements: dict[str, Any] = {}
        if spec_slide.title:
            elements["title"] = spec_slide.title
        if spec_slide.subtitle:
            elements["subtitle"] = spec_slide.subtitle
        if spec_slide.notes:
            elements["note"] = spec_slide.notes

        body_lines: list[str] = []
        for group_index, group in enumerate(spec_slide.bullets, start=1):
            texts = [bullet.text for bullet in group.items]
            if not texts:
                continue
            if group.anchor:
                elements[group.anchor] = texts
            else:
                body_lines.extend(texts)
        if body_lines:
            elements["body"] = body_lines

        for table_index, table in enumerate(spec_slide.tables, start=1):
            table_payload = {
                "headers": table.columns,
                "rows": table.rows,
            }
            key = table.anchor or f"table_{table_index}"
            elements[key] = table_payload

        for image_index, image in enumerate(spec_slide.images, start=1):
            key = image.anchor or f"image_{image_index}"
            elements[key] = {
                "source": str(image.source),
                "sizing": image.sizing,
            }
        for chart_index, chart in enumerate(spec_slide.charts, start=1):
            key = chart.anchor or f"chart_{chart_index}"
            elements[key] = {
                "type": chart.type,
                "categories": chart.categories,
                "series": [series.model_dump() for series in chart.series],
                "options": chart.options.model_dump() if chart.options else None,
            }
        for textbox_index, textbox in enumerate(spec_slide.textboxes, start=1):
            key = textbox.anchor or f"textbox_{textbox_index}"
            elements[key] = {
                "text": textbox.text,
            }
        return elements

    def _build_table_payload(
        self,
        *,
        item: MappingWorkItem,
        selected_profile: LayoutProfile | None,
        selected_layout: str,
    ) -> dict[str, Any] | None:
        if (
            item.content_slide is None
            or item.content_slide.elements is None
            or item.content_slide.elements.table_data is None
        ):
            return None

        payload = build_table_payload(item.content_slide.elements.table_data)
        if payload is None:
            return None

        placeholders = selected_profile.placeholders if selected_profile else ()
        anchor, reasons = resolve_table_anchor(item.spec_slide, placeholders)
        target_key = anchor or "table"
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "mapping table anchor resolved: slide_id=%s layout=%s anchor=%s reason=%s",
                self._resolve_slide_id(item),
                selected_profile.layout_id if selected_profile else selected_layout,
                target_key,
                ", ".join(reasons) if reasons else "none",
            )
        payload["_target_key"] = target_key
        return payload

    def _merge_table_payload(
        self,
        elements: dict[str, Any],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        target_key = payload.pop("_target_key", "table")
        cleaned = dict(elements)
        cleaned.pop("table", None)
        for key in list(cleaned.keys()):
            if key == target_key:
                continue
            if is_table_payload(cleaned[key]):
                cleaned.pop(key, None)
        cleaned[target_key] = payload
        return cleaned

    def _apply_capacity_controls(
        self,
        *,
        slide_id: str,
        layout: LayoutProfile | None,
        elements: dict[str, Any],
    ) -> tuple[
        MappingFallbackState,
        list[MappingAIPatch],
        list[str],
        list[MappingLogCapacityWarning],
    ]:
        fallback = MappingFallbackState()
        ai_patches: list[MappingAIPatch] = []
        warnings: list[str] = []
        capacity_warnings: list[MappingLogCapacityWarning] = []

        if layout is None:
            return fallback, ai_patches, warnings, capacity_warnings

        max_lines = layout.max_lines()
        max_chars = layout.max_chars()
        body = elements.get("body")
        if isinstance(body, list):
            structured = self._is_structured_body(body)
            body_lines = self._flatten_structured_body(body) if structured else body
            actual_lines = len(body_lines)
            actual_chars = self._count_body_chars(body_lines)
            overflow_lines = max_lines is not None and actual_lines > max_lines
            overflow_chars = max_chars is not None and actual_chars > max_chars
            if overflow_lines or overflow_chars:
                if overflow_lines:
                    warnings.append(
                        "body が許容行数 {max} を超過しているため LLM で調整します（元 {actual} 行）".format(
                            max=max_lines,
                            actual=actual_lines,
                        )
                    )
                    capacity_warnings.append(
                        MappingLogCapacityWarning(
                            slide_id=slide_id,
                            element="body",
                            max_lines=max_lines or 0,
                            actual_lines=actual_lines,
                            layout_id=layout.layout_id,
                        )
                    )
                if overflow_chars:
                    warnings.append(
                        "body が許容文字数 {max} を超過しているため LLM で調整します（元 {actual} 文字）".format(
                            max=max_chars,
                            actual=actual_chars,
                        )
                    )
                if structured:
                    warnings.append("body が type 付きブロックのため LLM 補正をスキップしました")
                else:
                    self._apply_text_fit(
                        slide_id=slide_id,
                        layout_id=layout.layout_id,
                        max_lines=max_lines,
                        max_chars=max_chars,
                        elements=elements,
                        original_body=body,
                        warnings=warnings,
                        ai_patches=ai_patches,
                    )

            updated_body = elements.get("body")
            if isinstance(updated_body, list) and not updated_body:
                warnings.append("body が空です")

        return fallback, ai_patches, warnings, capacity_warnings

    def _apply_text_fit(
        self,
        *,
        slide_id: str,
        layout_id: str | None,
        max_lines: int | None,
        max_chars: int | None,
        elements: dict[str, Any],
        original_body: list[str],
        warnings: list[str],
        ai_patches: list[MappingAIPatch],
    ) -> None:
        if self.text_fit_client is None:
            if self.text_fit_error:
                warnings.append(
                    f"LLM 補正をスキップしました（{self.text_fit_error}）"
                )
            else:
                warnings.append("LLM 補正クライアントが未設定のため本文を保持しました")
            return

        request = MappingTextFitRequest(
            slide_id=slide_id,
            layout_id=layout_id,
            max_lines=max_lines,
            max_chars=max_chars,
            body=list(original_body),
            subtitle=elements.get("subtitle"),
            note=elements.get("note"),
        )
        try:
            response = self.text_fit_client.fit(request)
        except (MappingTextFitClientExecutionError, MappingTextFitResponseFormatError) as exc:
            logger.warning(
                "mapping text fit failed: slide_id=%s layout=%s error=%s",
                slide_id,
                layout_id,
                exc,
            )
            warnings.append("LLM による本文調整に失敗したため本文を保持しました")
            return

        candidate_body = response.body
        if not candidate_body and original_body:
            warnings.append("LLM 出力が空のため適用しませんでした")
            return
        if not self._fits_constraints(candidate_body, max_lines, max_chars):
            warnings.append("LLM 出力が制約を満たさないため適用しませんでした")
            return

        patch_ops: list[JsonPatchOperation] = []
        if candidate_body != original_body:
            elements["body"] = candidate_body
            patch_ops.append(
                JsonPatchOperation(
                    op="replace",
                    path="/body",
                    value=candidate_body,
                )
            )

        if response.subtitle is not None and response.subtitle != elements.get("subtitle"):
            elements["subtitle"] = response.subtitle
            patch_ops.append(
                JsonPatchOperation(
                    op="replace",
                    path="/subtitle",
                    value=response.subtitle,
                )
            )

        if response.note is not None and response.note != elements.get("note"):
            elements["note"] = response.note
            patch_ops.append(
                JsonPatchOperation(
                    op="replace",
                    path="/note",
                    value=response.note,
                )
            )

        if patch_ops:
            ai_patches.append(
                MappingAIPatch(
                    patch_id=f"mapping-text-fit:{slide_id}",
                    description="LLM により本文を許容量内に調整",
                    patch=patch_ops,
                )
            )

    @staticmethod
    def _fits_constraints(
        body: list[str],
        max_lines: int | None,
        max_chars: int | None,
    ) -> bool:
        if max_lines is not None and len(body) > max_lines:
            return False
        if max_chars is not None and sum(len(line) for line in body) > max_chars:
            return False
        return True

    @staticmethod
    def _count_body_chars(body: list[str]) -> int:
        return sum(len(line) for line in body)

    @staticmethod
    def _is_structured_body(body: list[Any]) -> bool:
        return any(isinstance(item, dict) and "type" in item for item in body)

    @staticmethod
    def _flatten_structured_body(body: list[Any]) -> list[str]:
        lines: list[str] = []
        for entry in body:
            if isinstance(entry, dict):
                entry_type = entry.get("type")
                if entry_type == "bullets":
                    items = entry.get("items", [])
                    if isinstance(items, list):
                        for item in items:
                            lines.extend(MappingSlideProcessor._flatten_bullet_item(item))
                    continue
                if entry_type == "paragraph":
                    lines.extend(
                        MappingSlideProcessor._split_text(entry.get("text"), preserve_blank=True)
                    )
                    continue
                if entry_type == "custom":
                    lines.extend(
                        MappingSlideProcessor._split_text(entry.get("text"), preserve_blank=True)
                    )
                    lines.extend(
                        MappingSlideProcessor._split_text(entry.get("description"), preserve_blank=True)
                    )
                    continue
                lines.extend(
                    MappingSlideProcessor._split_text(entry.get("text"), preserve_blank=True)
                )
                continue
            if entry is None:
                continue
            lines.append(str(entry))
        return lines

    @staticmethod
    def _flatten_bullet_item(item: Any) -> list[str]:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            if not text:
                return []
            level_raw = item.get("level", 0)
            try:
                level = max(int(level_raw), 0)
            except (TypeError, ValueError):
                level = 0
            indent = "  " * level
            return [f"{indent}{text}"]
        if isinstance(item, str):
            text = item.strip()
            return [text] if text else []
        return []

    @staticmethod
    def _split_text(value: Any, *, preserve_blank: bool = False) -> list[str]:
        if not isinstance(value, str):
            return []
        segments = split_lines_preserve_blank(value)
        output: list[str] = []
        for segment in segments:
            stripped = segment.strip()
            if stripped:
                output.append(stripped)
            elif preserve_blank:
                output.append("")
        return output

    @staticmethod
    def _build_auto_draw_payload(spec_slide: Slide | None) -> list[dict[str, float]]:
        if spec_slide is None:
            return []
        return [
            {
                "anchor": anchor,
                "left_in": box.left_in,
                "top_in": box.top_in,
                "width_in": box.width_in,
                "height_in": box.height_in,
            }
            for anchor, box in spec_slide.auto_draw_boxes.items()
        ]
