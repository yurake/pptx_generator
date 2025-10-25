"""多形式インポート機能の実装。"""

from __future__ import annotations

import base64
import json
import shutil
import subprocess
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Iterable, Sequence
from urllib.parse import unquote_to_bytes, urlparse
from urllib.request import Request, urlopen

from ..models import ContentApprovalDocument, ContentDocumentMeta, ContentElements, ContentSlide


class ContentImportError(RuntimeError):
    """多形式インポートの失敗を表す。"""


@dataclass(slots=True)
class ContentImportResult:
    """インポートの結果。"""

    document: ContentApprovalDocument
    meta: dict[str, object]
    warnings: list[str]


@dataclass(slots=True)
class _SourcePayload:
    """入力ソースを読み込んだ結果。"""

    source: str
    kind: str
    text: str
    hash_value: str
    retrieved_at: datetime
    content_type: str | None
    warnings: list[str]


@dataclass(slots=True)
class _SourceProcessingResult:
    """ソースをスライドへ変換した結果。"""

    slides: list[ContentSlide]
    meta: dict[str, object]
    warnings: list[str]


class _HTMLTextExtractor(HTMLParser):
    """シンプルな HTML → テキスト変換器。"""

    def __init__(self) -> None:  # noqa: D401 - HTMLParser 初期化
        super().__init__()
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # noqa: D401
        if tag in {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:  # noqa: D401
        if tag in {"p", "div", "li"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:  # noqa: D401
        stripped = data.strip()
        if stripped:
            self._chunks.append(stripped)

    def get_text(self) -> str:
        lines = []
        buffer = ""
        for chunk in self._chunks:
            if chunk == "\n":
                if buffer:
                    lines.append(buffer)
                    buffer = ""
                continue
            buffer = f"{buffer} {chunk}".strip()
        if buffer:
            lines.append(buffer)
        return "\n".join(line.strip() for line in lines if line.strip())


class ContentImportService:
    """プレーンテキスト・PDF・URL を工程3向けドラフトへ正規化する。"""

    def __init__(
        self,
        *,
        libreoffice_path: Path | None = None,
        soffice_timeout_sec: int = 120,
        http_timeout_sec: int = 20,
    ) -> None:
        self._libreoffice_path = libreoffice_path
        self._soffice_timeout = soffice_timeout_sec
        self._http_timeout = http_timeout_sec

    # 公開 API ------------------------------------------------------------
    def import_sources(self, sources: Sequence[str]) -> ContentImportResult:
        """指定ソース群を解析し、content_draft 相当のドキュメントへ変換する。"""

        if not sources:
            msg = "入力ソースが指定されていません"
            raise ContentImportError(msg)

        slides: list[ContentSlide] = []
        meta_entries: list[dict[str, object]] = []
        warnings: list[str] = []

        for source in sources:
            payload = self._load_source(source)
            processed = self._convert_source(payload, start_index=len(slides))
            slides.extend(processed.slides)
            meta_entries.append(processed.meta)
            warnings.extend(processed.warnings)

        document = ContentApprovalDocument(
            slides=slides,
            meta=self._build_document_meta(slides),
        )
        meta = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_slides": len(slides),
            "sources": meta_entries,
        }
        return ContentImportResult(document=document, meta=meta, warnings=warnings)

    # 内部処理 ------------------------------------------------------------
    def _load_source(self, source: str) -> _SourcePayload:
        parsed = urlparse(source)
        if parsed.scheme in {"http", "https"}:
            return self._load_http_source(source)
        if parsed.scheme == "data":
            return self._load_data_uri(source)
        return self._load_file_source(source)

    def _load_file_source(self, source: str) -> _SourcePayload:
        path = Path(source).expanduser().resolve()
        if not path.exists():
            msg = f"入力ソースが見つかりません: {path}"
            raise ContentImportError(msg)

        suffix = path.suffix.lower()
        raw = path.read_bytes()
        hash_value = sha256(raw).hexdigest()
        retrieved_at = datetime.now(timezone.utc)
        warnings: list[str] = []

        if suffix == ".pdf":
            text = self._convert_pdf(path)
            content_type = "application/pdf"
        else:
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", errors="ignore")
                warnings.append("UTF-8 で解釈できない文字を無視しました")
            content_type = "text/plain"

        return _SourcePayload(
            source=str(path),
            kind="file",
            text=text,
            hash_value=hash_value,
            retrieved_at=retrieved_at,
            content_type=content_type,
            warnings=warnings,
        )

    def _load_http_source(self, source: str) -> _SourcePayload:
        headers = {"User-Agent": "pptx-generator/0.1"}
        request = Request(source, headers=headers)
        try:
            with urlopen(request, timeout=self._http_timeout) as response:  # noqa: S310
                raw = response.read()
                content_type = response.headers.get("Content-Type")
        except OSError as exc:  # noqa: PERF203
            msg = f"URL からの取得に失敗しました: {source}"
            raise ContentImportError(msg) from exc

        hash_value = sha256(raw).hexdigest()
        retrieved_at = datetime.now(timezone.utc)
        warnings: list[str] = []

        if content_type and "pdf" in content_type:
            with NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_file.write(raw)
                tmp_path = Path(tmp_file.name)
            try:
                text = self._convert_pdf(tmp_path)
            finally:
                tmp_path.unlink(missing_ok=True)
            return _SourcePayload(
                source=source,
                kind="url",
                text=text,
                hash_value=hash_value,
                retrieved_at=retrieved_at,
                content_type="application/pdf",
                warnings=warnings,
            )

        encoding = _extract_charset(content_type) or "utf-8"
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            text = raw.decode(encoding, errors="ignore")
            warnings.append("レスポンスのデコード時に無効なバイトを無視しました")

        if content_type and "html" in content_type:
            text = self._html_to_text(text)
        elif content_type and "json" in content_type:
            text = self._json_to_text(text, warnings)

        return _SourcePayload(
            source=source,
            kind="url",
            text=text,
            hash_value=hash_value,
            retrieved_at=retrieved_at,
            content_type=content_type,
            warnings=warnings,
        )

    def _load_data_uri(self, source: str) -> _SourcePayload:
        parsed = urlparse(source)
        if not parsed.path:
            msg = "data URI が空です"
            raise ContentImportError(msg)

        mime_and_data = parsed.path.split(",", maxsplit=1)
        if len(mime_and_data) != 2:
            msg = "data URI の形式が不正です"
            raise ContentImportError(msg)

        mime_part, data_part = mime_and_data
        is_base64 = mime_part.endswith(";base64")
        mime_type = mime_part.split(";", maxsplit=1)[0] if ";" in mime_part else mime_part
        raw: bytes
        if is_base64:
            raw = base64.b64decode(data_part)
        else:
            raw = unquote_to_bytes(data_part)

        hash_value = sha256(raw).hexdigest()
        retrieved_at = datetime.now(timezone.utc)
        warnings: list[str] = []

        if "pdf" in mime_type:
            with NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_file.write(raw)
                tmp_path = Path(tmp_file.name)
            try:
                text = self._convert_pdf(tmp_path)
            finally:
                tmp_path.unlink(missing_ok=True)
        else:
            encoding = _extract_charset(mime_part) or "utf-8"
            try:
                text = raw.decode(encoding)
            except UnicodeDecodeError:
                text = raw.decode(encoding, errors="ignore")
                warnings.append("data URI のデコード時に無効なバイトを無視しました")
            if "html" in mime_type:
                text = self._html_to_text(text)
            elif "json" in mime_type:
                text = self._json_to_text(text, warnings)

        return _SourcePayload(
            source=source,
            kind="data",
            text=text,
            hash_value=hash_value,
            retrieved_at=retrieved_at,
            content_type=mime_type or None,
            warnings=warnings,
        )

    def _convert_pdf(self, path: Path) -> str:
        soffice = self._libreoffice_path or shutil.which("soffice")
        if soffice is None:
            msg = "LibreOffice (soffice) が見つかりません。--libreoffice-path で指定してください"
            raise ContentImportError(msg)

        with TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            cmd = [
                str(soffice),
                "--headless",
                "--convert-to",
                "txt:Text (encoded):UTF8",
                str(path),
                "--outdir",
                str(output_dir),
            ]
            try:
                completed = subprocess.run(  # noqa: S603
                    cmd,
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=self._soffice_timeout,
                )
            except subprocess.TimeoutExpired as exc:
                msg = f"LibreOffice による PDF 変換がタイムアウトしました: {path}"
                raise ContentImportError(msg) from exc

            if completed.returncode != 0:
                msg = (
                    "LibreOffice による PDF 変換に失敗しました: "
                    f"{path}\nstdout: {completed.stdout}\nstderr: {completed.stderr}"
                )
                raise ContentImportError(msg)

            txt_path = output_dir / f"{path.stem}.txt"
            if not txt_path.exists():
                msg = f"LibreOffice 変換結果が見つかりません: {txt_path}"
                raise ContentImportError(msg)
            return txt_path.read_text(encoding="utf-8")

    def _convert_source(self, payload: _SourcePayload, *, start_index: int) -> _SourceProcessingResult:
        blocks = list(_split_into_blocks(payload.text))
        slides: list[ContentSlide] = []
        warnings = list(payload.warnings)

        if not blocks:
            warnings.append("入力ソースから利用可能なテキストブロックを抽出できませんでした")

        for offset, (title, lines) in enumerate(blocks, start=1):
            body_lines, truncated = _build_body_lines(lines)
            note = None
            if truncated:
                note = "本文が制限行数を超えたため一部を省略しました"
                warnings.append(
                    f"{payload.source}: '{title}' の本文を省略しました"
                )

            slide = ContentSlide(
                id=f"import-{start_index + offset:02d}",
                intent="imported",
                type_hint="content",
                elements=ContentElements(
                    title=_truncate(title, 120),
                    body=body_lines,
                    note=note,
                ),
                status="draft",
            )
            slides.append(slide)

        meta = {
            "source": payload.source,
            "kind": payload.kind,
            "retrieved_at": payload.retrieved_at.isoformat(),
            "hash": payload.hash_value,
            "content_type": payload.content_type,
            "slides": len(slides),
        }

        return _SourceProcessingResult(slides=slides, meta=meta, warnings=warnings)

    def _build_document_meta(self, slides: Sequence[ContentSlide]) -> ContentDocumentMeta | None:
        if not slides:
            return None

        first_title = slides[0].elements.title
        summary = f"{len(slides)} 件のインポートコンテンツ"
        if first_title:
            summary = f"{summary}: {first_title}"[:120]
        return ContentDocumentMeta(summary=summary)

    @staticmethod
    def _html_to_text(html: str) -> str:
        parser = _HTMLTextExtractor()
        parser.feed(html)
        parser.close()
        return parser.get_text()

    @staticmethod
    def _json_to_text(text: str, warnings: list[str]) -> str:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            warnings.append("JSON の解析に失敗したため生テキストを利用します")
            return text
        return json.dumps(payload, ensure_ascii=False, indent=2)


# ヘルパー -----------------------------------------------------------------


def _extract_charset(content_type: str | None) -> str | None:
    if not content_type:
        return None
    parts = [part.strip() for part in content_type.split(";")]
    for part in parts[1:]:
        if part.lower().startswith("charset="):
            return part.split("=", maxsplit=1)[1].strip()
    return None


def _split_into_blocks(text: str) -> Iterable[tuple[str, list[str]]]:
    current_title: str | None = None
    buffer: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            new_title = line.lstrip("#").strip()
            if current_title:
                yield current_title, buffer
            current_title = new_title or current_title or "Untitled"
            buffer = []
            continue
        if current_title is None:
            current_title = _truncate(line, 120)
            continue
        buffer.append(_strip_bullet_marker(line))

    if current_title:
        yield current_title, buffer


def _strip_bullet_marker(line: str) -> str:
    stripped = line.lstrip("-•*●\t ")
    return stripped if stripped else line.strip()


def _build_body_lines(lines: Sequence[str]) -> tuple[list[str], bool]:
    body: list[str] = []
    truncated = False
    for line in lines:
        wrapped = textwrap.wrap(
            line,
            width=40,
            replace_whitespace=True,
            drop_whitespace=True,
        )
        if not wrapped:
            continue
        for chunk in wrapped:
            body.append(chunk)
            if len(body) >= 6:
                truncated = True
                break
        if truncated:
            break

    if not body:
        body = ["(本文未設定)"]
    return body[:6], truncated


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit - 1]}…"

