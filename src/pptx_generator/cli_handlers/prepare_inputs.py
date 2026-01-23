from __future__ import annotations

import json
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any, Sequence

from pydantic import ValidationError

from urllib.parse import urlparse

from pptx_generator.content_import import ContentImportError, ContentImportResult, ContentImportService
from pptx_generator.utils.text_lines import normalize_line_list_preserve_blank

from pptx_generator.prepare.source import (
    PrepareSourceChapter,
    PrepareSourceDocument,
    PrepareSourceMeta,
    PrepareSourceSupportingPoint,
)

from .prepare_errors import PrepareCommandError


def load_prepare_inputs(
    inputs: Sequence[str],
) -> tuple[PrepareSourceDocument | None, list[dict[str, Any]], list[str]]:
    if not inputs:
        return None, [], []

    service = ContentImportService()
    documents: list[PrepareSourceDocument] = []
    metadata: list[dict[str, Any]] = []
    messages: list[str] = []

    for raw in inputs:
        value = raw.strip()
        if not value:
            continue
        document, per_source_meta, per_source_messages = load_prepare_input(value, service)
        documents.append(document)
        metadata.extend(per_source_meta)
        messages.extend(per_source_messages)

    if not documents:
        return None, metadata, messages

    combined_document = _combine_prepare_documents(documents)
    normalized_document = _normalize_import_chapter_ids(combined_document)
    return normalized_document, metadata, messages


def load_prepare_input(
    value: str,
    service: ContentImportService,
) -> tuple[PrepareSourceDocument, list[dict[str, Any]], list[str]]:
    parsed = urlparse(value)
    scheme = parsed.scheme.lower()
    if scheme == "http":
        raise PrepareCommandError(
            "HTTP スキームは許可されていません。HTTPS を利用してください",
            exit_code=2,
        )
    lower_value = value.lower()
    is_url = scheme == "https"
    is_data_uri = scheme == "data"
    candidate_path = Path(value).expanduser()
    path_exists = candidate_path.exists() and candidate_path.is_file()

    if path_exists and candidate_path.suffix.lower() not in {".pdf", ".html", ".htm"}:
        try:
            document = PrepareSourceDocument.parse_file(candidate_path)
        except UnicodeDecodeError:
            document, imported_meta, import_messages = _import_via_service(service, str(candidate_path))
            messages = [f"インポートを完了しました: {candidate_path}", *import_messages]
            return document, imported_meta, messages
        except (json.JSONDecodeError, ValidationError) as exc:
            if candidate_path.suffix.lower() in {".json", ".jsonc"}:
                raise PrepareCommandError(f"プレペア入力の解析に失敗しました: {exc}", exit_code=2) from exc
            document, imported_meta, import_messages = _import_via_service(service, str(candidate_path))
            messages = [f"インポートを完了しました: {candidate_path}", *import_messages]
            return document, imported_meta, messages

        metadata = [_build_structured_source_meta(candidate_path, document)]
        messages = [f"プレペア入力を読み込みました: {candidate_path}"]
        return document, metadata, messages

    if is_url or is_data_uri or path_exists:
        document, imported_meta, import_messages = _import_via_service(service, value)
        messages = [f"インポートを完了しました: {value}", *import_messages]
        return document, imported_meta, messages

    raise PrepareCommandError(f"プレペア入力を解釈できません: {value}", exit_code=2)


def _import_via_service(
    service: ContentImportService,
    source: str,
) -> tuple[PrepareSourceDocument, list[dict[str, Any]], list[str]]:
    try:
        result = service.import_sources([source])
    except ContentImportError as exc:
        raise PrepareCommandError(f"入力ソースの取り込みに失敗しました: {exc}", exit_code=2) from exc

    document = _convert_import_result_to_prepare_source(result, source)
    metadata: list[dict[str, Any]] = []
    sources_meta = result.meta.get("sources") if isinstance(result.meta, dict) else None
    if isinstance(sources_meta, list):
        for entry in sources_meta:
            if isinstance(entry, dict):
                copied = dict(entry)
                copied.setdefault("via", "content_import")
                metadata.append(copied)
    if not metadata:
        metadata.append(
            {
                "source": source,
                "kind": "import",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "via": "content_import",
            }
        )

    warning_messages = [f"警告: {warning}" for warning in result.warnings]
    return document, metadata, warning_messages


def _convert_import_result_to_prepare_source(
    result: ContentImportResult,
    source_label: str,
) -> PrepareSourceDocument:
    summary = (
        result.document.meta.summary
        if result.document.meta and result.document.meta.summary
        else source_label
    )
    meta = PrepareSourceMeta(
        title=summary[:120] if summary else "Imported Source",
        prepare_id=None,
        objective=None,
    )

    chapters: list[PrepareSourceChapter] = []
    raw_lines: list[str] = []

    for index, slide in enumerate(result.document.slides, start=1):
        title = slide.elements.title or f"{summary or 'Import'} {index:02d}"
        body_lines = normalize_line_list_preserve_blank(slide.elements.body or [])
        message_source = next((line for line in body_lines if line), None)
        message = message_source if message_source is not None else title
        supporting_points = [
            PrepareSourceSupportingPoint(statement=line)
            for line in body_lines[1:]
            if line
        ]
        chapter = PrepareSourceChapter(
            id=f"import-{index:02d}",
            title=title[:120],
            message=message,
            details=body_lines,
            supporting_points=supporting_points,
            story_hint=None,
            intent_tags=["imported"],
        )
        chapters.append(chapter)
        raw_lines.append(title)
        raw_lines.extend(body_lines)
        if slide.elements.note:
            raw_lines.append(slide.elements.note.strip())

    raw_text = "\n".join(raw_lines).strip() or None
    return PrepareSourceDocument(meta=meta, chapters=chapters, raw_text=raw_text)


def _combine_prepare_documents(documents: Sequence[PrepareSourceDocument]) -> PrepareSourceDocument:
    if not documents:
        raise ValueError("documents must not be empty")
    if len(documents) == 1:
        single = documents[0]
        return PrepareSourceDocument(
            meta=single.meta.model_copy(deep=True),
            chapters=[chapter.model_copy(deep=True) for chapter in single.chapters],
            raw_text=single.raw_text,
        )

    base_meta = documents[0].meta.model_copy(deep=True)
    chapters: list[PrepareSourceChapter] = []
    raw_texts: list[str] = []
    objectives: list[str] = []

    for doc in documents:
        chapters.extend(chapter.model_copy(deep=True) for chapter in doc.chapters)
        if doc.raw_text:
            raw_texts.append(doc.raw_text)
        if doc.meta.objective:
            objectives.append(doc.meta.objective)

    if objectives:
        base_meta.objective = "\n\n".join(objectives)

    raw_text = "\n\n".join(text for text in raw_texts if text.strip()) or None

    return PrepareSourceDocument(meta=base_meta, chapters=chapters, raw_text=raw_text)


def _normalize_import_chapter_ids(document: PrepareSourceDocument) -> PrepareSourceDocument:
    next_index = 1
    seen_ids: set[str] = set()
    normalized_chapters: list[PrepareSourceChapter] = []
    changed = False

    for chapter in document.chapters:
        new_id = chapter.id
        if new_id.startswith("import-"):
            new_id = f"import-{next_index:02d}"
            next_index += 1
            while new_id in seen_ids:
                new_id = f"import-{next_index:02d}"
                next_index += 1
            if new_id != chapter.id:
                changed = True
        elif new_id in seen_ids:
            pass

        seen_ids.add(new_id)
        if new_id == chapter.id:
            normalized_chapters.append(chapter)
            continue
        normalized_chapters.append(chapter.model_copy(update={"id": new_id}))

    if not changed:
        return document

    return PrepareSourceDocument(
        meta=document.meta.model_copy(deep=True),
        chapters=[chapter.model_copy(deep=True) for chapter in normalized_chapters],
        raw_text=document.raw_text,
    )


def _build_structured_source_meta(
    path: Path,
    document: PrepareSourceDocument,
) -> dict[str, Any]:
    try:
        raw_bytes = path.read_bytes()
    except OSError:
        raw_bytes = b""
    hash_value = hashlib.sha256(raw_bytes).hexdigest() if raw_bytes else None
    metadata = {
        "source": str(path),
        "kind": "file",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "hash": f"sha256:{hash_value}" if hash_value else None,
        "chapters": len(document.chapters),
        "content_type": _guess_structured_content_type(path.suffix.lower()),
        "via": "structured",
    }
    return {key: value for key, value in metadata.items() if value is not None}


def _guess_structured_content_type(suffix: str) -> str:
    mapping = {
        ".json": "application/json",
        ".jsonc": "application/json",
        ".md": "text/markdown",
        ".markdown": "text/markdown",
        ".txt": "text/plain",
    }
    return mapping.get(suffix, "text/plain")


__all__ = [
    "load_prepare_inputs",
    "load_prepare_input",
]
