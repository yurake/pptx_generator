"""工程3 ブリーフ成果物を読み込むステップ。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..brief import BriefCard, BriefDocument, BriefGenerationMeta, BriefLogEntry
from ..models import (
    ContentApprovalDocument,
    ContentDocumentMeta,
    ContentElements,
    ContentSlide,
)
from .base import PipelineContext, PipelineStep

logger = logging.getLogger(__name__)


class BriefNormalizationError(RuntimeError):
    """ブリーフ成果物の読み込み失敗を表す。"""


@dataclass(slots=True)
class BriefNormalizationOptions:
    """ブリーフ成果物読込の設定。"""

    cards_path: Path | None = None
    log_path: Path | None = None
    ai_meta_path: Path | None = None
    require_document: bool = False


class BriefNormalizationStep:
    """BriefCard 成果物を読み込むパイプラインステップ。"""

    name = "brief_normalization"

    def __init__(self, options: BriefNormalizationOptions | None = None) -> None:
        self.options = options or BriefNormalizationOptions()

    def run(self, context: PipelineContext) -> None:
        document = self._load_document(self.options.cards_path)
        if document is None:
            if self.options.require_document:
                msg = "ブリーフカードファイルが指定されていません"
                raise BriefNormalizationError(msg)
            logger.info("brief_cards が指定されていないため brief_normalization をスキップします")
            return

        context.add_artifact("brief_document", document)
        if self.options.cards_path:
            context.add_artifact("brief_document_path", str(self.options.cards_path.resolve()))

        logs = self._load_logs(self.options.log_path)
        if logs is not None:
            context.add_artifact("brief_log", logs)

        meta = self._load_generation_meta(self.options.ai_meta_path)
        if meta is not None:
            context.add_artifact("brief_generation_meta", meta)

        # 互換用: ContentApprovalDocument を生成して既存ステップへ渡す
        compatibility_document, compatibility_meta = self._build_compatibility_content(document)
        context.add_artifact("content_approved", compatibility_document)
        context.add_artifact("content_approved_meta", compatibility_meta)

    # ------------------------------------------------------------------ #
    # private helpers
    # ------------------------------------------------------------------ #
    def _load_document(self, path: Path | None) -> BriefDocument | None:
        if path is None:
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            msg = f"prepare_card.json を読み込めません: {path}"
            raise BriefNormalizationError(msg) from exc
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            msg = f"prepare_card.json の解析に失敗しました: {path}"
            raise BriefNormalizationError(msg) from exc
        try:
            return BriefDocument.model_validate(payload)
        except ValueError as exc:
            msg = f"prepare_card.json の検証に失敗しました: {path}"
            raise BriefNormalizationError(msg) from exc

    def _load_logs(self, path: Path | None) -> list[BriefLogEntry] | None:
        if path is None:
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            msg = f"brief_log.json を読み込めません: {path}"
            raise BriefNormalizationError(msg) from exc
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            msg = f"brief_log.json の解析に失敗しました: {path}"
            raise BriefNormalizationError(msg) from exc
        if not isinstance(payload, list):
            msg = "brief_log.json は配列形式である必要があります"
            raise BriefNormalizationError(msg)
        entries: list[BriefLogEntry] = []
        for index, item in enumerate(payload):
            try:
                entries.append(BriefLogEntry.model_validate(item))
            except ValueError as exc:
                msg = f"brief_log.json の検証に失敗しました: index={index}"
                raise BriefNormalizationError(msg) from exc
        return entries

    def _load_generation_meta(self, path: Path | None) -> BriefGenerationMeta | None:
        if path is None:
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            msg = f"ai_generation_meta.json を読み込めません: {path}"
            raise BriefNormalizationError(msg) from exc
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            msg = f"ai_generation_meta.json の解析に失敗しました: {path}"
            raise BriefNormalizationError(msg) from exc
        try:
            return BriefGenerationMeta.model_validate(payload)
        except ValueError as exc:
            msg = f"ai_generation_meta.json の検証に失敗しました: {path}"
            raise BriefNormalizationError(msg) from exc

    def _build_compatibility_content(
        self,
        document: BriefDocument,
    ) -> tuple[ContentApprovalDocument, dict[str, Any]]:
        slides = [self._convert_card_to_slide(card, index) for index, card in enumerate(document.cards, start=1)]
        meta = ContentDocumentMeta(
            tone=document.story_context.tone,
            audience=None,
            summary=f"{document.brief_id} のブリーフカード（互換生成）"[:120],
        )
        content_document = ContentApprovalDocument(slides=slides, meta=meta)
        meta_payload = {
            "brief_id": document.brief_id,
            "cards": [card.card_id for card in document.cards],
            "hash": document.compute_content_hash(),
        }
        return content_document, meta_payload

    def _convert_card_to_slide(self, card: BriefCard, index: int) -> ContentSlide:
        title = card.message[:120] or card.chapter
        body = self._build_body_lines(card)
        elements = ContentElements(title=title, body=body, table_data=None, note=None)
        intent = card.intent_tags[0] if card.intent_tags else card.story.phase
        return ContentSlide(
            id=card.card_id or f"brief-{index:03d}",
            intent=intent,
            type_hint=card.story.phase,
            elements=elements,
            status="draft",
            ai_review=None,
            applied_autofix=card.autofix_applied,
        )

    def _build_body_lines(self, card: BriefCard) -> list[str]:
        lines: list[str] = []

        def append_text(text: str) -> None:
            text = text.strip()
            if not text:
                return
            chunks = [text[i : i + 40] for i in range(0, len(text), 40)]
            for chunk in chunks:
                if len(lines) >= 6:
                    return
                lines.append(chunk)

        for paragraph in card.narrative:
            append_text(paragraph)
            if len(lines) >= 6:
                break
        if len(lines) < 6 and card.supporting_points:
            for point in card.supporting_points:
                append_text(point.statement)
                if len(lines) >= 6:
                    break
        if not lines:
            append_text(card.message)
        return lines[:6]
