"""stage 3 プレペア成果物を読み込むステップ。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
import textwrap
from typing import Any

from ..prepare import (
    PrepareBodyBlock,
    PrepareCard,
    PrepareDocument,
    PrepareGenerationMeta,
    PrepareLogEntry,
)
from ..models import (
    ContentApprovalDocument,
    ContentDocumentMeta,
    ContentElements,
    ContentSlide,
    ContentSlideSource,
    ContentTableData,
)
from ..utils.text_lines import split_lines_preserve_blank
from .base import PipelineContext, PipelineStage, PipelineStep

logger = logging.getLogger(__name__)


class PrepareNormalizationError(RuntimeError):
    """プレペア成果物の読み込み失敗を表す。"""


@dataclass(slots=True)
class PrepareNormalizationOptions:
    """プレペア成果物読込の設定。"""

    cards_path: Path | None = None
    log_path: Path | None = None
    ai_meta_path: Path | None = None
    require_document: bool = False


class PrepareNormalizationStep:
    """PrepareCard 成果物を読み込むパイプラインステップ。"""

    name = "prepare_normalization"
    stage = PipelineStage.PREPARE

    def __init__(self, options: PrepareNormalizationOptions | None = None) -> None:
        self.options = options or PrepareNormalizationOptions()

    def run(self, context: PipelineContext) -> None:
        logger.info("prepare_normalization start cards_path=%s", self.options.cards_path)
        document = self._load_document(self.options.cards_path)
        if document is None:
            if self.options.require_document:
                msg = "プレペアカードファイルが指定されていません"
                raise PrepareNormalizationError(msg)
            logger.info("prepare_cards が指定されていないため prepare_normalization をスキップします")
            return

        context.add_artifact("prepare_document", document)
        if self.options.cards_path:
            context.add_artifact("prepare_document_path", str(self.options.cards_path.resolve()))
            logger.info("prepare_normalization loaded prepare_cards=%s", self.options.cards_path.resolve())

        base_dir = self.options.cards_path.parent if self.options.cards_path else Path.cwd()
        document_meta = document.meta if isinstance(document.meta, dict) else {}

        log_path = self.options.log_path
        if log_path is None:
            meta_value = document_meta.get("prepare_log_path") if document_meta else None
            log_path = self._resolve_meta_path(meta_value, base_dir)
        if log_path is None and self.options.cards_path is not None:
            candidate = self.options.cards_path.parent / "prepare_log.json"
            if candidate.exists():
                log_path = candidate
        if log_path is not None and not log_path.exists():
            log_path = None

        logs = self._load_logs(log_path)
        if logs is not None:
            context.add_artifact("prepare_log", logs)
            logger.info("prepare_normalization loaded prepare_log=%s", log_path.resolve())

        ai_meta_path = self.options.ai_meta_path
        if ai_meta_path is None:
            meta_value = document_meta.get("ai_generation_meta_path") if document_meta else None
            ai_meta_path = self._resolve_meta_path(meta_value, base_dir)
        if ai_meta_path is None and self.options.cards_path is not None:
            candidate = self.options.cards_path.parent / "ai_generation_meta.json"
            if candidate.exists():
                ai_meta_path = candidate
        if ai_meta_path is not None and not ai_meta_path.exists():
            ai_meta_path = None

        meta = self._load_generation_meta(ai_meta_path)
        if meta is not None:
            context.add_artifact("prepare_generation_meta", meta)
            meta_path_str = str(ai_meta_path.resolve()) if ai_meta_path else "auto-resolved"
            logger.info("prepare_normalization loaded ai_generation_meta=%s", meta_path_str)

        # 互換用: ContentApprovalDocument を生成して既存ステップへ渡す
        compatibility_document, compatibility_meta = self._build_compatibility_content(document)
        context.add_artifact("content_approved", compatibility_document)
        context.add_artifact("content_approved_meta", compatibility_meta)
        logger.info("prepare_normalization completed")

    # ------------------------------------------------------------------ #
    # private helpers
    # ------------------------------------------------------------------ #
    def _load_document(self, path: Path | None) -> PrepareDocument | None:
        if path is None:
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            msg = f"prepare_card.json を読み込めません: {path}"
            raise PrepareNormalizationError(msg) from exc
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            msg = f"prepare_card.json の解析に失敗しました: {path}"
            raise PrepareNormalizationError(msg) from exc
        payload = self._normalize_prepare_payload(payload)
        try:
            return PrepareDocument.model_validate(payload)
        except ValueError as exc:
            msg = f"prepare_card.json の検証に失敗しました: {path}"
            raise PrepareNormalizationError(msg) from exc

    def _load_logs(self, path: Path | None) -> list[PrepareLogEntry] | None:
        if path is None:
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            msg = f"prepare_log.json を読み込めません: {path}"
            raise PrepareNormalizationError(msg) from exc
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            msg = f"prepare_log.json の解析に失敗しました: {path}"
            raise PrepareNormalizationError(msg) from exc
        if not isinstance(payload, list):
            msg = "prepare_log.json は配列形式である必要があります"
            raise PrepareNormalizationError(msg)
        entries: list[PrepareLogEntry] = []
        for index, item in enumerate(payload):
            try:
                entries.append(PrepareLogEntry.model_validate(item))
            except ValueError as exc:
                msg = f"prepare_log.json の検証に失敗しました: index={index}"
                raise PrepareNormalizationError(msg) from exc
        return entries

    @staticmethod
    def _normalize_prepare_payload(payload: dict[str, Any]) -> dict[str, Any]:
        """旧スキーマとの互換性維持のため、タイトル項目を調整する。"""

        cards = payload.get("cards")
        if isinstance(cards, list):
            for card in cards:
                content = card.get("content")
                if not isinstance(content, dict):
                    continue
                title = content.get("title")
                headline = content.get("headline")
                if title and headline:
                    # 旧スキーマでは title+headline の両方が入るケースがあり、headline を優先して title を落とす
                    content.pop("title", None)
        return payload

    def _load_generation_meta(self, path: Path | None) -> PrepareGenerationMeta | None:
        if path is None:
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            msg = f"ai_generation_meta.json を読み込めません: {path}"
            raise PrepareNormalizationError(msg) from exc
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            msg = f"ai_generation_meta.json の解析に失敗しました: {path}"
            raise PrepareNormalizationError(msg) from exc
        try:
            return PrepareGenerationMeta.model_validate(payload)
        except ValueError as exc:
            msg = f"ai_generation_meta.json の検証に失敗しました: {path}"
            raise PrepareNormalizationError(msg) from exc

    def _build_compatibility_content(
        self,
        document: PrepareDocument,
    ) -> tuple[ContentApprovalDocument, dict[str, Any]]:
        phase_counts: dict[str, int] = {}
        slides = [
            self._convert_card_to_slide(card, index, phase_counts)
            for index, card in enumerate(document.cards, start=1)
        ]
        meta = ContentDocumentMeta(
            tone=document.story_context.tone,
            audience=None,
            summary=f"{document.prepare_id} のプレペアカード（互換生成）"[:120],
        )
        content_document = ContentApprovalDocument(slides=slides, meta=meta)
        meta_payload = {
            "prepare_id": document.prepare_id,
            "cards": [card.card_id for card in document.cards],
            "hash": document.compute_content_hash(),
        }
        return content_document, meta_payload

    @staticmethod
    def _resolve_meta_path(value: object, base_dir: Path) -> Path | None:
        if not value:
            return None
        try:
            candidate = Path(str(value))
        except TypeError:
            return None
        if candidate.is_absolute():
            return candidate
        return (base_dir / candidate).resolve()

    def _convert_card_to_slide(
        self,
        card: PrepareCard,
        index: int,
        phase_counts: dict[str, int],
    ) -> ContentSlide:
        title = card.headline_or_title()[:120]
        body = self._build_body_lines(card)
        notes_text = card.notes_text()
        subtitle = card.subtitle_or_chapter()
        table_data = self._extract_table_data(card)
        elements = ContentElements(
            title=title,
            subtitle=subtitle,
            body=body,
            table_data=table_data,
            note="\n".join(notes_text) if notes_text else None,
        )
        intent = card.primary_intent() or card.role.story_phase or "unlabeled"
        phase_key = (card.role.story_phase or intent or "unlabeled").lower()
        phase_counts[phase_key] = phase_counts.get(phase_key, 0) + 1
        blueprint_meta = card.blueprint_meta()
        if blueprint_meta and blueprint_meta.get("slot_id"):
            slide_id = str(blueprint_meta.get("slot_id"))
        else:
            slide_id = card.card_id or f"prepare-{index:03d}"

        intent_tags = card.resolved_intent_tags()
        if intent and intent not in intent_tags:
            intent_tags.append(intent)

        source = ContentSlideSource(
            card_id=card.card_id,
            order=card.order,
            story_phase=card.role.story_phase,
            intent_tags=tuple(intent_tags),
            blueprint=blueprint_meta if isinstance(blueprint_meta, dict) else None,
        )

        return ContentSlide(
            id=slide_id,
            intent=intent,
            type_hint=card.role.story_phase or intent,
            elements=elements,
            status="draft",
            ai_review=None,
            applied_autofix=[],
            source=source,
        )

    def _build_body_lines(self, card: PrepareCard) -> list[str]:
        lines: list[str] = []
        for block in card.content.body:
            lines.extend(self._collect_block_lines(block))

        if lines:
            return lines

        headline = card.headline_or_title().strip()
        return [headline] if headline else []

    def _collect_block_lines(self, block: PrepareBodyBlock) -> list[str]:
        if block.type == "table":
            return []

        if block.type == "bullets":
            return self._lines_from_bullets(block.data)

        lines: list[str] = []
        lines.extend(self._split_text(block.text, preserve_blank=True))
        lines.extend(self._split_text(block.description, preserve_blank=True))
        return lines

    def _lines_from_bullets(self, raw_items: Any) -> list[str]:
        items = raw_items.get("items") if isinstance(raw_items, dict) else None
        if not isinstance(items, list):
            return []

        lines: list[str] = []
        for entry in items:
            lines.extend(self._lines_from_bullet_entry(entry))
        return lines

    def _lines_from_bullet_entry(self, entry: Any) -> list[str]:
        if isinstance(entry, dict):
            text = str(entry.get("text") or "").strip()
            if not text:
                return []
            level = self._extract_bullet_level(entry.get("level", 0))
            prefix = "  " * level
            return [f"{prefix}{segment}" for segment in self._split_text(text)]

        if isinstance(entry, str):
            return self._split_text(entry)

        return []

    @staticmethod
    def _extract_bullet_level(value: Any) -> int:
        try:
            return max(int(value), 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _split_text(value: Any, *, preserve_blank: bool = False) -> list[str]:
        if not isinstance(value, str):
            return []

        segments = split_lines_preserve_blank(value)
        output: list[str] = []
        for segment in segments:
            stripped = segment.strip()
            if not stripped:
                if preserve_blank:
                    output.append("")
                continue
            if len(stripped) <= 200:
                output.append(stripped)
                continue
            wrapped = textwrap.wrap(
                stripped,
                width=200,
                drop_whitespace=True,
                break_long_words=True,
            )
            output.extend(chunk.strip() for chunk in wrapped if chunk.strip())
        return output

    @staticmethod
    def _extract_table_data(card: PrepareCard) -> ContentTableData | None:
        for block in card.content.body:
            if block.type != "table":
                continue
            if not block.rows:
                continue
            headers = list(block.headers or [])
            rows = [list(row) for row in block.rows]
            return ContentTableData(headers=headers, rows=rows)
        return None
