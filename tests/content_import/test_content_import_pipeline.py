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
