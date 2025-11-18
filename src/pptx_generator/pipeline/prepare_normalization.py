"""工程3 プレペア成果物を読み込むステップ。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..prepare import PrepareCard, PrepareDocument, PrepareGenerationMeta, PrepareLogEntry
from ..models import (
    ContentApprovalDocument,
    ContentDocumentMeta,
    ContentElements,
    ContentSlide,
)
from .base import PipelineContext, PipelineStep

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

    def __init__(self, options: PrepareNormalizationOptions | None = None) -> None:
        self.options = options or PrepareNormalizationOptions()

    def run(self, context: PipelineContext) -> None:
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

        logs = self._load_logs(self.options.log_path)
        if logs is not None:
            context.add_artifact("prepare_log", logs)

        meta = self._load_generation_meta(self.options.ai_meta_path)
        if meta is not None:
            context.add_artifact("prepare_generation_meta", meta)

        # 互換用: ContentApprovalDocument を生成して既存ステップへ渡す
        compatibility_document, compatibility_meta = self._build_compatibility_content(document)
        context.add_artifact("content_approved", compatibility_document)
        context.add_artifact("content_approved_meta", compatibility_meta)

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

    def _convert_card_to_slide(self, card: PrepareCard, index: int, phase_counts: dict[str, int]) -> ContentSlide:
        title = (card.content.title or card.headline_or_title())[:120]
        body = self._build_body_lines(card)
        notes_text = card.notes_text()
        elements = ContentElements(
            title=title,
            body=body,
            table_data=None,
            note="\n".join(notes_text) if notes_text else None,
        )
        intent = card.primary_intent()

        phase = card.role.story_phase
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
        blueprint_meta = card.blueprint_meta()
        if blueprint_meta and blueprint_meta.get("slot_id"):
            slide_id = str(blueprint_meta.get("slot_id"))
        else:
            slide_id = card.card_id or f"prepare-{index:03d}"

        return ContentSlide(
            id=slide_id,
            intent=intent,
            type_hint=card.role.story_phase,
            elements=elements,
            status="draft",
            ai_review=None,
            applied_autofix=[],
        )

    def _build_body_lines(self, card: PrepareCard) -> list[str]:
        lines: list[str] = []
        max_lines = 6

        def append_text(text: str) -> None:
            text = text.strip()
            if not text:
                return
            idx = 0
            while idx < len(text) and len(lines) < max_lines:
                lines.append(text[idx : idx + 40])
                idx += 40

        for block in card.content.body:
            if len(lines) >= max_lines:
                break

            text = (block.text or "").strip()
            if text:
                for line in text.splitlines():
                    append_text(line)
                    if len(lines) >= max_lines:
                        break
                if len(lines) >= max_lines:
                    break

            items: list[str] = []
            if block.data:
                raw_items = block.data.get("items")
                if isinstance(raw_items, list):
                    for value in raw_items:
                        if isinstance(value, str) and value.strip():
                            items.append(value.strip())
                        elif isinstance(value, dict):
                            line = str(value.get("text") or "").strip()
                            if line:
                                items.append(line)
            for item in items:
                if len(lines) >= max_lines:
                    break
                for line in item.splitlines():
                    append_text(f"- {line}")
                    if len(lines) >= max_lines:
                        break

        if not lines:
            headline = card.headline_or_title().strip()
            if headline:
                for line in headline.splitlines():
                    append_text(line)
                    if len(lines) >= max_lines:
                        break

        return lines
