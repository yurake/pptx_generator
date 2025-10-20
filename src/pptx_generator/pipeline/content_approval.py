"""工程3 承認済みコンテンツを読み込むステップ。"""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Callable, Iterable

from pydantic import ValidationError

from ..models import (ContentApprovalDocument, ContentDocumentMeta,
                      ContentElements, ContentReviewLogEntry, ContentSlide,
                      ContentTableData, JobSpec, Slide, SlideBullet,
                      SlideBulletGroup, SlideTable)
from .base import PipelineContext

logger = logging.getLogger(__name__)


class ContentApprovalError(RuntimeError):
    """承認済みコンテンツの読み込み失敗を表す。"""


@dataclass(slots=True)
class ContentApprovalOptions:
    """承認済みコンテンツ読込の設定。"""

    approved_path: Path | None = None
    review_log_path: Path | None = None
    require_document: bool = False
    require_all_approved: bool = True
    fallback_builder: Callable[[JobSpec], ContentApprovalDocument] | None = None


class ContentApprovalStep:
    """承認済みコンテンツとレビューログを読み込むパイプラインステップ。"""

    name = "content_approval"

    def __init__(self, options: ContentApprovalOptions | None = None) -> None:
        self.options = options or ContentApprovalOptions()

    def run(self, context: PipelineContext) -> None:
        document: ContentApprovalDocument | None = None
        meta: dict[str, object] | None = None
        loaded_from_file = False
        generated_from_spec = False

        if self.options.approved_path is not None:
            document, meta = self._load_document_with_meta(self.options.approved_path)
            loaded_from_file = True
        elif self.options.fallback_builder is not None:
            document = self.options.fallback_builder(context.spec)
            meta = self._build_generated_meta(document)
            generated_from_spec = True

        if document is not None and meta is not None:
            if self.options.require_all_approved:
                self._ensure_all_approved(document)

            updated_ids = self._apply_to_spec(context.spec, document)
            meta["applied_to_spec"] = bool(updated_ids)
            meta["updated_slide_ids"] = updated_ids

            context.add_artifact("content_approved", document)
            context.add_artifact("content_approved_meta", meta)

            if loaded_from_file:
                logger.info(
                    "承認済みコンテンツを読み込みました: slides=%d",
                    len(document.slides),
                )
            elif generated_from_spec:
                logger.info(
                    "承認済みコンテンツを Spec から生成しました: slides=%d",
                    len(document.slides),
                )
        elif self.options.require_document:
            msg = "承認済みコンテンツファイルが指定されていません"
            raise ContentApprovalError(msg)

        if self.options.review_log_path is not None:
            logs, meta = self._load_review_logs_with_meta(self.options.review_log_path)
            context.add_artifact("content_review_log", logs)
            context.add_artifact("content_review_log_meta", meta)
            logger.info("承認ログを読み込みました: events=%d", len(logs))

    @staticmethod
    def _load_document_with_meta(
        path: Path,
    ) -> tuple[ContentApprovalDocument, dict[str, object]]:
        try:
            raw_text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            msg = f"承認済みコンテンツファイルを読み込めません: {path}"
            raise ContentApprovalError(msg) from exc

        sanitized = _strip_json_comments(raw_text)
        try:
            payload = json.loads(sanitized)
        except json.JSONDecodeError as exc:
            msg = f"承認済みコンテンツ JSON の解析に失敗しました: {path}"
            raise ContentApprovalError(msg) from exc

        try:
            document = ContentApprovalDocument.model_validate(payload)
        except ValidationError as exc:
            msg = f"承認済みコンテンツの検証に失敗しました: {path}"
            raise ContentApprovalError(msg) from exc

        meta = {
            "path": str(path.resolve()),
            "hash": _hash_string(sanitized),
            "slides": len(document.slides),
            "slide_ids": [slide.id for slide in document.slides],
        }
        return document, meta

    @staticmethod
    def _load_review_logs_with_meta(
        path: Path,
    ) -> tuple[list[ContentReviewLogEntry], dict[str, object]]:
        try:
            raw_text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            msg = f"承認ログファイルを読み込めません: {path}"
            raise ContentApprovalError(msg) from exc

        sanitized = _strip_json_comments(raw_text)
        try:
            payload = json.loads(sanitized)
        except json.JSONDecodeError as exc:
            msg = f"承認ログ JSON の解析に失敗しました: {path}"
            raise ContentApprovalError(msg) from exc

        if not isinstance(payload, list):
            msg = "承認ログは配列形式である必要があります"
            raise ContentApprovalError(msg)

        entries: list[ContentReviewLogEntry] = []
        action_counter: Counter[str] = Counter()
        for index, item in enumerate(payload):
            try:
                entry = ContentReviewLogEntry.model_validate(item)
            except ValidationError as exc:
                msg = f"承認ログの検証に失敗しました: index={index}"
                raise ContentApprovalError(msg) from exc
            entries.append(entry)
            action_counter.update([entry.action])

        meta = {
            "path": str(path.resolve()),
            "hash": _hash_string(sanitized),
            "events": len(entries),
            "actions": dict(action_counter),
        }
        return entries, meta

    @staticmethod
    def build_document_from_spec(spec: JobSpec) -> ContentApprovalDocument:
        slides = [_build_content_slide(slide) for slide in spec.slides]
        summary_text = f"{spec.meta.title} の Spec から生成された承認済みコンテンツ"
        meta = ContentDocumentMeta(
            tone=getattr(spec.meta, "theme", None),
            audience=spec.meta.client,
            summary=summary_text[:120],
        )
        return ContentApprovalDocument(slides=slides, meta=meta)

    @staticmethod
    def _ensure_all_approved(document: ContentApprovalDocument) -> None:
        not_approved = [
            slide.id for slide in document.slides if slide.status != "approved"
        ]
        if not_approved:
            joined = ", ".join(not_approved)
            msg = f"承認済みドキュメントに未承認カードが含まれています: {joined}"
            raise ContentApprovalError(msg)

    def _apply_to_spec(
        self, spec: JobSpec, document: ContentApprovalDocument
    ) -> list[str]:
        cards = {
            slide.id: slide
            for slide in document.slides
            if slide.status == "approved"
        }
        if not cards:
            return []

        updated_ids: list[str] = []
        for slide in spec.slides:
            card = cards.get(slide.id)
            if card is None:
                continue
            self._merge_slide(slide, card.elements)
            updated_ids.append(slide.id)
        return updated_ids

    def _merge_slide(self, slide: Slide, elements: ContentElements) -> None:
        slide.title = elements.title
        if elements.note is not None:
            slide.notes = elements.note
        if elements.body:
            self._merge_body(slide, elements.body)
        if elements.table_data is not None:
            self._merge_table(slide, elements.table_data.headers, elements.table_data.rows)

    def _merge_body(self, slide: Slide, lines: list[str]) -> None:
        remaining = list(lines)
        groups = slide.bullets

        existing_ids = {
            bullet.id for group in groups for bullet in group.items if bullet.id
        }

        if not groups:
            new_items: list[SlideBullet] = []
            while remaining:
                text = remaining.pop(0)
                bullet_id = self._generate_bullet_id(slide.id, existing_ids)
                new_items.append(SlideBullet(id=bullet_id, text=text, level=0))
            if new_items:
                slide.bullets = [SlideBulletGroup(anchor=None, items=new_items)]
            return

        for group in groups:
            items = group.items
            idx = 0
            while idx < len(items):
                if remaining:
                    text = remaining.pop(0)
                    items[idx].text = text
                    items[idx].level = 0
                    idx += 1
                else:
                    del items[idx:]
                    break

        while remaining:
            text = remaining.pop(0)
            bullet_id = self._generate_bullet_id(slide.id, existing_ids)
            new_bullet = SlideBullet(id=bullet_id, text=text, level=0)
            if slide.bullets and slide.bullets[-1].anchor is None:
                slide.bullets[-1].items.append(new_bullet)
            else:
                slide.bullets.append(
                    SlideBulletGroup(anchor=None, items=[new_bullet])
                )

        slide.bullets = [group for group in slide.bullets if group.items]

    def _merge_table(
        self, slide: Slide, headers: list[str], rows: list[list[str]]
    ) -> None:
        if not slide.tables:
            return
        table = slide.tables[0]
        if headers:
            table.columns = list(headers)
        table.rows = [list(row) for row in rows]

    @staticmethod
    def _generate_bullet_id(slide_id: str, existing: set[str]) -> str:
        index = 1
        while True:
            candidate = f"{slide_id}-approved-{index}"
            if candidate not in existing:
                existing.add(candidate)
                return candidate
            index += 1

    @staticmethod
    def _build_generated_meta(document: ContentApprovalDocument) -> dict[str, object]:
        return {
            "source": "spec",
            "slides": len(document.slides),
            "slide_ids": [slide.id for slide in document.slides],
        }


def _build_content_slide(slide: Slide) -> ContentSlide:
    elements = _build_content_elements(slide)
    intent = slide.layout or slide.id
    return ContentSlide(
        id=slide.id,
        intent=intent,
        elements=elements,
        status="approved",
    )


def _build_content_elements(slide: Slide) -> ContentElements:
    title = slide.title or slide.subtitle or slide.layout or slide.id
    body = list(_iter_body_lines(slide, limit=6))
    if not body and slide.subtitle:
        body = [_trim(slide.subtitle)]
    table_data = _build_table_data(slide.tables[0]) if slide.tables else None
    note = slide.notes
    return ContentElements(
        title=title,
        body=body,
        table_data=table_data,
        note=note,
    )


def _build_table_data(table: SlideTable) -> ContentTableData | None:
    headers = getattr(table, "columns", [])
    rows = getattr(table, "rows", [])
    if not headers and not rows:
        return None
    return ContentTableData(headers=list(headers), rows=[list(row) for row in rows])


def _iter_body_lines(slide: Slide, *, limit: int) -> Iterable[str]:
    count = 0
    for group in slide.bullets:
        for bullet in group.items:
            raw_text = bullet.text.strip() if bullet.text else ""
            if not raw_text:
                continue
            prefix = "" if bullet.level <= 0 else "  " * bullet.level
            yield _trim(f"{prefix}{raw_text}")
            count += 1
            if count >= limit:
                return


def _trim(text: str, width: int = 40) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= width:
        return normalized
    if width <= 3:
        return normalized[:width]
    return normalized[: width - 3] + "..."


def _strip_json_comments(source: str) -> str:
    """JSONC 形式のコメントを除去する。"""

    result: list[str] = []
    i = 0
    length = len(source)
    in_string = False
    escape = False

    while i < length:
        ch = source[i]
        if in_string:
            result.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            result.append(ch)
            i += 1
            continue

        if ch == "/" and i + 1 < length:
            nxt = source[i + 1]
            if nxt == "/":
                i += 2
                while i < length and source[i] not in ("\n", "\r"):
                    i += 1
                continue
            if nxt == "*":
                i += 2
                while i + 1 < length and not (
                    source[i] == "*" and source[i + 1] == "/"
                ):
                    i += 1
                i += 2
                continue

        result.append(ch)
        i += 1

    return "".join(result)


def _hash_string(source: str) -> str:
    digest = sha256(source.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
