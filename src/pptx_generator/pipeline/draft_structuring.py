"""工程4 ドラフト構成設計ステップ。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from ..models import (ContentApprovalDocument, ContentSlide, DraftDocument,
                      DraftLayoutCandidate, DraftMeta, DraftSection,
                      DraftSlideCard, JobSpec)
from ..api.draft_store import DraftStore, BoardAlreadyExistsError
from .base import PipelineContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DraftStructuringOptions:
    """ドラフト構成ステップの設定。"""

    layouts_path: Path | None = None
    output_dir: Path | None = None
    draft_filename: str = "draft_draft.json"
    approved_filename: str = "draft_approved.json"
    log_filename: str = "draft_review_log.json"
    target_length: int | None = None
    structure_pattern: str | None = None
    appendix_limit: int = 5


class DraftStructuringError(RuntimeError):
    """ドラフト構成処理の失敗を表す。"""


@dataclass(slots=True)
class LayoutRecord:
    """layouts.jsonl の 1 レコード。"""

    layout_id: str
    usage_tags: tuple[str, ...]
    text_hint: dict[str, object]
    media_hint: dict[str, object]


class DraftStructuringStep:
    """content_approved と layouts.jsonl から Draft ドキュメントを生成する。"""

    name = "draft_structuring"

    def __init__(self, options: DraftStructuringOptions | None = None) -> None:
        self.options = options or DraftStructuringOptions()

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def run(self, context: PipelineContext) -> None:
        artifact = context.artifacts.get("content_approved")
        if artifact is None:
            logger.info("content_approved が存在しないため draft_structuring をスキップします")
            return
        if not isinstance(artifact, ContentApprovalDocument):
            msg = "content_approved artifact の型が不正です"
            raise DraftStructuringError(msg)
        document = artifact

        layouts = self._load_layouts(self.options.layouts_path)
        draft = self._build_document(context.spec, document, layouts)

        output_dir = self.options.output_dir or context.workdir
        output_dir.mkdir(parents=True, exist_ok=True)

        draft_path = output_dir / self.options.draft_filename
        approved_path = output_dir / self.options.approved_filename
        log_path = output_dir / self.options.log_filename

        self._write_document(draft_path, draft)
        self._write_document(approved_path, draft)
        self._write_log(log_path, [])

        context.add_artifact("draft_document", draft)
        context.add_artifact("draft_document_path", str(approved_path))
        context.add_artifact("draft_review_log_path", str(log_path))

        spec_id = self._spec_id_from_title(getattr(context.spec.meta, "title", None))
        context.add_artifact("draft_spec_id", spec_id)

        store = DraftStore()
        try:
            store.create_board(spec_id, draft)
        except BoardAlreadyExistsError:
            store.overwrite_board(spec_id, draft)

        logger.info(
            "Draft ドキュメントを生成しました: sections=%d",
            len(draft.sections),
        )

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _load_layouts(self, path: Path | None) -> list[LayoutRecord]:
        if path is None:
            logger.info("layouts.jsonl が指定されていないため、候補スコアは既定値を使用します")
            return []

        records: list[LayoutRecord] = []
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            msg = f"layouts.jsonl を読み込めません: {path}"
            raise DraftStructuringError(msg) from exc

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                msg = f"layouts.jsonl の解析に失敗しました: {path}"
                raise DraftStructuringError(msg) from exc

            layout_id = payload.get("layout_id")
            if not layout_id:
                logger.debug("layout_id が存在しないレコードをスキップ: %s", payload)
                continue

            record = LayoutRecord(
                layout_id=layout_id,
                usage_tags=tuple(str(tag) for tag in payload.get("usage_tags", [])),
                text_hint=payload.get("text_hint") or {},
                media_hint=payload.get("media_hint") or {},
            )
            records.append(record)
        return records

    def _build_document(
        self,
        spec: JobSpec,
        document: ContentApprovalDocument,
        layouts: Sequence[LayoutRecord],
    ) -> DraftDocument:
        slides_by_id = {slide.id: slide for slide in document.slides}

        sections: list[DraftSection] = []
        section_map: dict[str, DraftSection] = {}

        for index, spec_slide in enumerate(spec.slides, start=1):
            content_slide = slides_by_id.get(spec_slide.id)
            if content_slide is None:
                logger.debug("content_approved に存在しないスライドをスキップ: %s", spec_slide.id)
                continue

            section_key, section_name = self._resolve_section(content_slide, spec_slide)
            section = section_map.get(section_key)
            if section is None:
                section = DraftSection(
                    name=section_name,
                    order=len(section_map) + 1,
                    status="draft",
                )
                section_map[section_key] = section
                sections.append(section)

            card_order = len(section.slides) + 1
            card = self._build_card(content_slide, spec_slide.layout, layouts, order=card_order)
            section.slides.append(card)

        meta = DraftMeta(
            target_length=self.options.target_length or sum(len(section.slides) for section in sections),
            structure_pattern=self.options.structure_pattern or "custom",
            appendix_limit=self.options.appendix_limit,
        )

        return DraftDocument(sections=sections, meta=meta)

    def _resolve_section(self, content_slide: ContentSlide, spec_slide) -> tuple[str, str]:
        story = getattr(content_slide, "story", None)
        if story:
            chapter_id = story.get("chapter_id") if isinstance(story, dict) else story.chapter_id
            phase = story.get("phase") if isinstance(story, dict) else story.phase
            if chapter_id:
                return str(chapter_id), str(chapter_id)
            if phase:
                return str(phase), str(phase)

        if content_slide.intent:
            return content_slide.intent, content_slide.intent
        return spec_slide.layout, spec_slide.layout

    def _build_card(
        self,
        content_slide: ContentSlide,
        default_layout: str,
        layouts: Sequence[LayoutRecord],
        *,
        order: int,
    ) -> DraftSlideCard:
        candidates = self._score_candidates(content_slide, layouts)
        layout_hint = candidates[0].layout_id if candidates else default_layout

        return DraftSlideCard(
            ref_id=content_slide.id,
            order=order,
            layout_hint=layout_hint,
            locked=False,
            status="draft",
            layout_candidates=candidates[:5],
            appendix=False,
        )

    def _score_candidates(
        self,
        content_slide: ContentSlide,
        layouts: Sequence[LayoutRecord],
    ) -> list[DraftLayoutCandidate]:
        if not layouts:
            return []

        scores: list[DraftLayoutCandidate] = []
        for record in layouts:
            score = self._score_layout(record, content_slide)
            if score <= 0.0:
                continue
            scores.append(DraftLayoutCandidate(layout_id=record.layout_id, score=round(score, 3)))

        scores.sort(key=lambda candidate: candidate.score, reverse=True)
        return scores

    def _score_layout(self, record: LayoutRecord, slide: ContentSlide) -> float:
        score = 0.1
        usage_tags = set(tag.lower() for tag in record.usage_tags)

        if slide.intent and slide.intent.lower() in usage_tags:
            score += 0.4

        if slide.type_hint and slide.type_hint.lower() in usage_tags:
            score += 0.3

        body_length = len(slide.elements.body)
        max_lines = self._safe_int(record.text_hint.get("max_lines"))
        if max_lines is not None:
            if body_length <= max_lines:
                score += 0.1
            else:
                score -= min(0.2, (body_length - max_lines) * 0.05)

        has_table = slide.elements.table_data is not None
        allow_table = bool(record.media_hint.get("allow_table"))
        if has_table and allow_table:
            score += 0.1
        elif has_table and not allow_table:
            score -= 0.3

        score = max(0.0, min(1.0, score))
        return score

    @staticmethod
    def _safe_int(value: object) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _write_document(path: Path, document: DraftDocument) -> None:
        payload = document.model_dump(mode="json")
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _write_log(path: Path, entries: Iterable[dict[str, object]]) -> None:
        payload = list(entries)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _spec_id_from_title(title: str | None) -> str:
        if not title:
            return "default"
        normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in title)
        normalized = normalized.strip("-") or "default"
        return normalized[:64]
