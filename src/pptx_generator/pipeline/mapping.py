"""工程5 マッピングステップ。"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..models import (
    ContentApprovalDocument,
    ContentSlide,
    DraftDocument,
    DraftMeta,
    DraftSection,
    DraftSlideCard,
    MappingAIPatch,
    MappingCandidate,
    MappingFallbackState,
    MappingLog,
    MappingLogMeta,
    MappingLogSlide,
    MappingSlideMeta,
    RenderingReadyDocument,
    RenderingReadyMeta,
    RenderingReadySlide,
    JsonPatchOperation,
    Slide,
    JobSpec,
)
from .base import PipelineContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MappingOptions:
    """マッピング工程の設定。"""

    layouts_path: Path | None = None
    output_dir: Path | None = None
    rendering_ready_filename: str = "rendering_ready.json"
    mapping_log_filename: str = "mapping_log.json"
    fallback_report_filename: str | None = "fallback_report.json"
    max_candidates: int = 5
    template_path: Path | None = None


@dataclass(slots=True)
class LayoutProfile:
    """layouts.jsonl のレコードを抽象化したもの。"""

    layout_id: str
    usage_tags: tuple[str, ...]
    text_hint: Mapping[str, Any]
    media_hint: Mapping[str, Any]

    def allows_table(self) -> bool:
        return bool(self.media_hint.get("allow_table"))

    def max_lines(self) -> int | None:
        value = self.text_hint.get("max_lines")
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None


class MappingStep:
    """承認済みドラフトを基に rendering_ready.json を生成するステップ。"""

    name = "mapping"

    def __init__(self, options: MappingOptions | None = None) -> None:
        self.options = options or MappingOptions()

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def run(self, context: PipelineContext) -> None:
        start = time.perf_counter()
        draft_document = self._require_draft_document(context)
        content_document = self._optional_content_document(context)
        layout_catalog = self._load_layout_catalog(self.options.layouts_path)

        section_lookup = self._build_section_lookup(draft_document)
        card_lookup = self._build_card_lookup(draft_document)
        content_lookup = (
            {slide.id: slide for slide in content_document.slides}
            if content_document is not None
            else {}
        )

        rendering_slides: list[RenderingReadySlide] = []
        log_slides: list[MappingLogSlide] = []
        fallback_records: list[dict[str, Any]] = []
        fallback_slide_ids: set[str] = set()
        ai_patch_count = 0
        ai_patch_slide_ids: set[str] = set()
        previous_layout: str | None = None

        for index, slide in enumerate(context.spec.slides, start=1):
            card = card_lookup.get(slide.id)
            content_slide = content_lookup.get(slide.id)
            section_name = section_lookup.get(slide.id)

            candidates = self._score_candidates(
                slide_id=slide.id,
                content_slide=content_slide,
                layout_catalog=layout_catalog,
                previous_layout=previous_layout,
            )
            if card and card.layout_candidates:
                # layout_candidates から score を引き継ぎ、欠損分を補う
                merged = {
                    candidate.layout_id: candidate.score
                    for candidate in candidates
                }
                for candidate in card.layout_candidates:
                    merged.setdefault(candidate.layout_id, candidate.score)
                candidates = [
                    MappingCandidate(layout_id=layout_id, score=score)
                    for layout_id, score in merged.items()
                ]
                candidates.sort(key=lambda candidate: candidate.score, reverse=True)
                candidates = candidates[: self.options.max_candidates]

            selected_layout = self._select_layout(slide.layout, card, candidates)
            previous_layout = selected_layout

            elements = self._build_elements(slide)
            fallback_state, ai_patches, warnings = self._apply_capacity_controls(
                slide_id=slide.id,
                layout=layout_catalog.get(selected_layout),
                elements=elements,
            )

            if fallback_state.applied:
                fallback_slide_ids.add(slide.id)
                fallback_records.append(
                    {
                        "slide_id": slide.id,
                        "history": list(fallback_state.history),
                        "reason": fallback_state.reason,
                    }
                )
            if ai_patches:
                ai_patch_count += len(ai_patches)
                ai_patch_slide_ids.add(slide.id)

            rendering_slides.append(
                RenderingReadySlide(
                    layout_id=selected_layout,
                    elements=elements,
                    meta=MappingSlideMeta(
                        section=section_name,
                        page_no=index,
                        sources=[slide.id],
                        fallback=fallback_state.history[-1]
                        if fallback_state.applied and fallback_state.history
                        else "none",
                    ),
                )
            )

            log_slides.append(
                MappingLogSlide(
                    ref_id=slide.id,
                    selected_layout=selected_layout,
                    candidates=candidates[: self.options.max_candidates],
                    fallback=fallback_state,
                    ai_patch=ai_patches,
                    warnings=warnings,
                )
            )

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        rendering_meta = RenderingReadyMeta(
            template_version=self._resolve_template_version(context),
            content_hash=self._resolve_content_hash(context),
            generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            job_meta=context.spec.meta,
            job_auth=context.spec.auth,
        )
        rendering_document = RenderingReadyDocument(
            slides=rendering_slides,
            meta=rendering_meta,
        )
        mapping_log = MappingLog(
            slides=log_slides,
            meta=MappingLogMeta(
                mapping_time_ms=elapsed_ms,
                fallback_count=len(fallback_slide_ids),
                ai_patch_count=ai_patch_count,
            ),
        )

        output_dir = self.options.output_dir or context.workdir
        output_dir.mkdir(parents=True, exist_ok=True)

        rendering_path = output_dir / self.options.rendering_ready_filename
        rendering_path.write_text(
            json.dumps(
                rendering_document.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        mapping_log_path = output_dir / self.options.mapping_log_filename
        mapping_log_path.write_text(
            json.dumps(
                mapping_log.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        if fallback_records and self.options.fallback_report_filename:
            fallback_path = output_dir / self.options.fallback_report_filename
            fallback_path.write_text(
                json.dumps(
                    {
                        "generated_at": rendering_meta.generated_at,
                        "slides": fallback_records,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            context.add_artifact("mapping_fallback_report_path", str(fallback_path))

        context.add_artifact("rendering_ready", rendering_document)
        context.add_artifact("rendering_ready_path", str(rendering_path))
        context.add_artifact("mapping_log", mapping_log)
        context.add_artifact("mapping_log_path", str(mapping_log_path))
        mapping_meta = {
            "elapsed_ms": elapsed_ms,
            "slides": len(rendering_slides),
            "fallback_count": len(fallback_slide_ids),
            "fallback_slide_ids": sorted(fallback_slide_ids),
            "ai_patch_count": ai_patch_count,
            "ai_patch_slide_ids": sorted(ai_patch_slide_ids),
            "rendering_ready_generated_at": rendering_meta.generated_at,
            "template_version": rendering_meta.template_version,
            "content_hash": rendering_meta.content_hash,
            "rendering_ready_path": str(rendering_path),
        }
        context.add_artifact("mapping_meta", mapping_meta)

        logger.info(
            "rendering_ready.json を生成しました: slides=%d fallback=%d ai_patch=%d",
            len(rendering_slides),
            len(fallback_slide_ids),
            ai_patch_count,
        )

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _require_draft_document(self, context: PipelineContext) -> DraftDocument:
        draft_document = context.artifacts.get("draft_document")
        if draft_document is None:
            logger.info("draft_document が存在しないため簡易ドラフトを生成します")
            fallback = self._build_fallback_draft(context.spec)
            context.add_artifact("draft_document", fallback)
            return fallback
        if not isinstance(draft_document, DraftDocument):
            logger.warning("draft_document artifact の型が不正のため簡易ドラフトを生成します")
            fallback = self._build_fallback_draft(context.spec)
            context.add_artifact("draft_document", fallback)
            return fallback
        return draft_document

    @staticmethod
    def _optional_content_document(
        context: PipelineContext,
    ) -> ContentApprovalDocument | None:
        document = context.artifacts.get("content_approved")
        if document is None:
            return None
        if not isinstance(document, ContentApprovalDocument):
            logger.warning("content_approved artifact の型が不正のため無視します")
            return None
        return document

    def _load_layout_catalog(
        self, path: Path | None
    ) -> dict[str, LayoutProfile]:
        if path is None:
            return {}
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("layouts.jsonl が見つからないため既定値を使用します: %s", path)
            return {}
        catalog: dict[str, LayoutProfile] = {}
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                logger.debug("layouts.jsonl の 1 レコード解析に失敗しました: %s", line)
                continue
            layout_id = payload.get("layout_id")
            if not layout_id:
                continue
            catalog[layout_id] = LayoutProfile(
                layout_id=layout_id,
                usage_tags=tuple(str(tag).lower() for tag in payload.get("usage_tags", [])),
                text_hint=payload.get("text_hint") or {},
                media_hint=payload.get("media_hint") or {},
            )
        return catalog

    @staticmethod
    def _build_section_lookup(draft_document: DraftDocument) -> dict[str, str]:
        lookup: dict[str, str] = {}
        for section in draft_document.sections:
            for card in section.slides:
                lookup[card.ref_id] = section.name
        return lookup

    @staticmethod
    def _build_card_lookup(
        draft_document: DraftDocument,
    ) -> dict[str, DraftSlideCard]:
        lookup: dict[str, DraftSlideCard] = {}
        for section in draft_document.sections:
            for card in section.slides:
                lookup[card.ref_id] = card
        return lookup

    def _score_candidates(
        self,
        *,
        slide_id: str,
        content_slide: ContentSlide | None,
        layout_catalog: Mapping[str, LayoutProfile],
        previous_layout: str | None,
    ) -> list[MappingCandidate]:
        intent = (content_slide.intent if content_slide else None) or ""
        intent = intent.lower()
        type_hint = (
            (content_slide.type_hint if content_slide else None) or ""
        ).lower()
        body_lines = (
            len(content_slide.elements.body) if content_slide and content_slide.elements else 0
        )
        has_table = (
            bool(content_slide.elements.table_data)
            if content_slide and content_slide.elements
            else False
        )

        candidates: list[MappingCandidate] = []
        for profile in layout_catalog.values():
            score = 0.0

            if intent and intent in profile.usage_tags:
                score += 0.5
            if type_hint and type_hint in profile.usage_tags:
                score += 0.15
            if profile.max_lines() is not None:
                if body_lines <= profile.max_lines():
                    score += 0.3
                else:
                    score -= min(0.3, (body_lines - profile.max_lines()) * 0.05)
            elif body_lines <= 6:
                score += 0.1
            if has_table:
                score += 0.05 if profile.allows_table() else -0.2
            if previous_layout and profile.layout_id == previous_layout:
                score -= 0.05

            score = max(0.0, min(1.0, round(score, 3)))
            if score <= 0.0:
                continue
            candidates.append(
                MappingCandidate(layout_id=profile.layout_id, score=score)
            )
        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        return candidates[: self.options.max_candidates]

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

    @staticmethod
    def _build_elements(slide: Slide) -> dict[str, Any]:
        elements: dict[str, Any] = {}
        if slide.title:
            elements["title"] = slide.title
        if slide.subtitle:
            elements["subtitle"] = slide.subtitle
        if slide.notes:
            elements["note"] = slide.notes

        body_lines: list[str] = []
        for group_index, group in enumerate(slide.bullets, start=1):
            texts = [bullet.text for bullet in group.items]
            if not texts:
                continue
            if group.anchor:
                elements[group.anchor] = texts
            else:
                body_lines.extend(texts)
        if body_lines:
            elements["body"] = body_lines

        for table_index, table in enumerate(slide.tables, start=1):
            table_payload = {
                "headers": table.columns,
                "rows": table.rows,
            }
            key = table.anchor or f"table_{table_index}"
            elements[key] = table_payload

        for image_index, image in enumerate(slide.images, start=1):
            key = image.anchor or f"image_{image_index}"
            elements[key] = {
                "source": str(image.source),
                "sizing": image.sizing,
            }
        for chart_index, chart in enumerate(slide.charts, start=1):
            key = chart.anchor or f"chart_{chart_index}"
            elements[key] = {
                "type": chart.type,
                "categories": chart.categories,
                "series": [series.model_dump() for series in chart.series],
                "options": chart.options.model_dump() if chart.options else None,
            }
        for textbox_index, textbox in enumerate(slide.textboxes, start=1):
            key = textbox.anchor or f"textbox_{textbox_index}"
            elements[key] = {
                "text": textbox.text,
            }
        return elements

    def _apply_capacity_controls(
        self,
        *,
        slide_id: str,
        layout: LayoutProfile | None,
        elements: dict[str, Any],
    ) -> tuple[MappingFallbackState, list[MappingAIPatch], list[str]]:
        fallback = MappingFallbackState()
        ai_patches: list[MappingAIPatch] = []
        warnings: list[str] = []

        if layout is None:
            return fallback, ai_patches, warnings

        max_lines = layout.max_lines()
        body = elements.get("body")
        if max_lines is not None and isinstance(body, list) and len(body) > max_lines:
            truncated = body[:max_lines]
            warnings.append(
                f"body が許容行数 {max_lines} を超過したため truncate しました"
            )
            fallback.applied = True
            fallback.history.append("shrink_text")
            fallback.reason = f"body_lines={len(body)} max_lines={max_lines}"
            elements["body"] = truncated
            ai_patches.append(
                MappingAIPatch(
                    patch_id=f"{slide_id}-shrink-text",
                    description=f"本文を {max_lines} 行に短縮",
                    patch=[
                        JsonPatchOperation(
                            op="replace",
                            path="/elements/body",
                            value=truncated,
                        )
                    ],
                )
            )

        if isinstance(body, list) and not body:
            warnings.append("body が空です")

        return fallback, ai_patches, warnings

    def _resolve_template_version(self, context: PipelineContext) -> str | None:
        branding = context.artifacts.get("branding")
        if isinstance(branding, dict):
            source = branding.get("source")
            if isinstance(source, dict):
                template = source.get("template")
                if isinstance(template, str):
                    return Path(template).stem
        if self.options.template_path is not None:
            return self.options.template_path.stem
        return None

    @staticmethod
    def _resolve_content_hash(context: PipelineContext) -> str | None:
        meta = context.artifacts.get("content_approved_meta")
        if isinstance(meta, dict):
            hash_value = meta.get("hash")
            if isinstance(hash_value, str):
                return hash_value
        return None

    @staticmethod
    def _build_fallback_draft(spec: JobSpec) -> DraftDocument:
        section = DraftSection(name="auto", order=1, slides=[])
        for index, slide in enumerate(spec.slides, start=1):
            section.slides.append(
                DraftSlideCard(
                    ref_id=slide.id,
                    order=index,
                    layout_hint=slide.layout,
                    locked=False,
                    status="draft",
                    layout_candidates=[],
                    appendix=False,
                )
            )
        meta = DraftMeta(
            target_length=len(section.slides),
            structure_pattern="auto",
            appendix_limit=0,
        )
        return DraftDocument(sections=[section], meta=meta)
