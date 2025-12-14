from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from pptx_generator.content_import import ContentImportError, ContentImportService


def test_import_from_text_file(tmp_path: Path) -> None:
    source = tmp_path / "draft.txt"
    source.write_text("# 背景\n- 課題A\n- 課題B\n\n# 提案\n提案内容を整理", encoding="utf-8")

    service = ContentImportService()
    result = service.import_sources([str(source)])

    assert result.document.slides
    assert result.document.slides[0].status == "draft"
    assert result.document.slides[0].elements.title == "背景"
    assert result.document.slides[0].elements.body
    assert result.meta["total_slides"] == len(result.document.slides)
    assert not result.warnings


def test_import_from_data_uri() -> None:
    data_uri = "data:text/plain;charset=utf-8,%23%20タイトル%0A本文ライン"

    service = ContentImportService()
    result = service.import_sources([data_uri])

    slide = result.document.slides[0]
    assert slide.elements.title.startswith("タイトル")
    assert slide.elements.body[0]


def test_import_without_sources_raises() -> None:
    service = ContentImportService()
    with pytest.raises(ContentImportError):
        service.import_sources([])


def test_import_from_local_html(tmp_path: Path) -> None:
    source = tmp_path / "page.html"
    source.write_text("<h1>Summary</h1><p>売上が前年比+20%です</p>", encoding="utf-8")

    service = ContentImportService()
    result = service.import_sources([str(source)])

    slide = result.document.slides[0]
    body_joined = "\n".join(slide.elements.body)
    assert "Summary" in slide.elements.title or "Summary" in body_joined
    assert "<" not in body_joined
    assert result.meta["total_slides"] == len(result.document.slides)


def test_import_from_local_json(tmp_path: Path) -> None:
    source = tmp_path / "payload.json"
    source.write_text('{"title": "Hello", "body": "World"}', encoding="utf-8")

    service = ContentImportService()
    result = service.import_sources([str(source)])

    slide = result.document.slides[0]
    text_joined = "\n".join(slide.elements.body)
    assert '"title": "Hello"' in text_joined
    assert "<" not in text_joined
    assert result.meta["total_slides"] == len(result.document.slides)


def test_convert_pdf_retries_with_writer_infilter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock")
    output_text = "converted text"

    service = ContentImportService(libreoffice_path="/usr/bin/soffice")

    calls: list[CompletedProcess[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> CompletedProcess[str]:
        outdir = Path(cmd[-1])
        if "--infilter=writer_pdf_import" in cmd:
            (outdir / f"{pdf_path.stem}.txt").write_text(output_text, encoding="utf-8")
            stdout = "writer import success"
            stderr = ""
        else:
            stdout = "draw import"
            stderr = "Error: Please verify input parameters..."
        proc = CompletedProcess(cmd, 0, stdout, stderr)
        calls.append(proc)
        return proc

    monkeypatch.setattr("pptx_generator.content_import.service.subprocess.run", fake_run)

    text = service._convert_pdf(pdf_path)

    assert text == output_text
    assert len(calls) == 2
    assert any("--infilter=writer_pdf_import" in call.args for call in calls)


def test_convert_pdf_error_message_contains_stdout_and_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdf_path = tmp_path / "broken.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 broken content")

    service = ContentImportService(libreoffice_path="/usr/bin/soffice")

    def fake_run(cmd: list[str], **kwargs: object) -> CompletedProcess[str]:
        stdout = "draw import failure"
        stderr = "Error: Please verify input parameters..."
        return CompletedProcess(cmd, 0, stdout, stderr)

    monkeypatch.setattr("pptx_generator.content_import.service.subprocess.run", fake_run)

    with pytest.raises(ContentImportError) as exc_info:
        service._convert_pdf(pdf_path)

    message = str(exc_info.value)
    assert "draw import failure" in message
    assert "Error: Please verify input parameters..." in message


def test_load_http_source_handles_uppercase_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ContentImportService()

    convert_called = False

    def fake_convert_pdf(self: ContentImportService, path: Path) -> str:  # noqa: D401
        nonlocal convert_called
        convert_called = True
        assert path.exists()
        return "converted from pdf"

    class FakeResponse:
        headers = {"Content-Type": "APPLICATION/PDF"}

        def read(self) -> bytes:  # noqa: D401
            return b"%PDF-1.4 mock"

        def __enter__(self) -> "FakeResponse":  # noqa: D401
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: D401, ANN001
            return False

    def fake_urlopen(request: object, timeout: int = 0) -> FakeResponse:  # noqa: D401, ANN001
        return FakeResponse()

    monkeypatch.setattr("pptx_generator.content_import.service.urlopen", fake_urlopen)
    monkeypatch.setattr(ContentImportService, "_convert_pdf", fake_convert_pdf)

    payload = service._load_http_source("https://example.com/file.pdf")

    assert convert_called
    assert payload.content_type == "application/pdf"
    assert payload.text == "converted from pdf"


def test_load_data_uri_handles_uppercase_html() -> None:
    data_uri = "data:TEXT/HTML;charset=utf-8,%3Ch1%3ETitle%3C/h1%3E%0A%3Cp%3EBody%3C/p%3E"

    service = ContentImportService()
    payload = service._load_data_uri(data_uri)

    assert "Title" in payload.text
    assert "Body" in payload.text
    assert "<" not in payload.text


def test_load_http_source_handles_uppercase_html(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ContentImportService()

    class FakeResponse:
        headers = {"Content-Type": "TEXT/HTML; charset=utf-8"}

        def read(self) -> bytes:  # noqa: D401
            return b"<h1>Heading</h1><p>body</p>"

        def __enter__(self) -> "FakeResponse":  # noqa: D401
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: D401, ANN001
            return False

    def fake_urlopen(request: object, timeout: int = 0) -> FakeResponse:  # noqa: D401, ANN001
        return FakeResponse()

    monkeypatch.setattr("pptx_generator.content_import.service.urlopen", fake_urlopen)

    payload = service._load_http_source("https://example.com/page.html")

    assert "Heading" in payload.text
    assert "body" in payload.text
    assert "<" not in payload.text


def test_load_http_source_handles_uppercase_json(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ContentImportService()

    class FakeResponse:
        headers = {"Content-Type": "APPLICATION/JSON"}

        def read(self) -> bytes:  # noqa: D401
            return b'{"title": "Hello"}'

        def __enter__(self) -> "FakeResponse":  # noqa: D401
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: D401, ANN001
            return False

    def fake_urlopen(request: object, timeout: int = 0) -> FakeResponse:  # noqa: D401, ANN001
        return FakeResponse()

    monkeypatch.setattr("pptx_generator.content_import.service.urlopen", fake_urlopen)

    payload = service._load_http_source("https://example.com/data.json")

    assert '"title": "Hello"' in payload.text
    assert "<" not in payload.text


def test_load_data_uri_handles_uppercase_json() -> None:
    data_uri = "data:APPLICATION/JSON;charset=utf-8,%7B%22title%22%3A%22Hello%22%7D"

    service = ContentImportService()
    payload = service._load_data_uri(data_uri)

    assert '"title": "Hello"' in payload.text
    assert "<" not in payload.text
