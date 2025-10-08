"""CLI の統合テスト。"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from click.testing import CliRunner
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from pptx_generator.cli import app
from pptx_generator.models import JobSpec
from pptx_generator.pipeline import pdf_exporter


def test_cli_run_generates_outputs(tmp_path) -> None:
    spec_path = Path("samples/sample_spec.json")
    workdir = tmp_path / "work"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "run",
            str(spec_path),
            "--workdir",
            str(workdir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    spec = JobSpec.parse_file(spec_path)

    outputs_dir = workdir / "outputs"
    pptx_path = outputs_dir / "proposal.pptx"
    analysis_path = outputs_dir / "analysis.json"
    audit_path = outputs_dir / "audit_log.json"

    assert pptx_path.exists()
    assert analysis_path.exists()
    assert audit_path.exists()

    payload = json.loads(analysis_path.read_text(encoding="utf-8"))
    assert payload.get("slides") == len(spec.slides)
    assert isinstance(payload.get("issues"), list)
    assert isinstance(payload.get("fixes"), list)
    assert payload.get("meta", {}).get("title") == spec.meta.title

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit_payload.get("slides") == len(spec.slides)
    assert audit_payload.get("pdf_export") is None
    assert isinstance(audit_payload.get("refiner_adjustments"), list)

    presentation = Presentation(pptx_path)
    assert len(presentation.slides) == len(spec.slides)

    for slide_spec, slide in zip(spec.slides, presentation.slides, strict=False):
        if slide_spec.title is None:
            continue
        actual = slide.shapes.title.text if slide.shapes.title else None
        assert actual == slide_spec.title

    agenda_slide = presentation.slides[1]
    tables = [shape for shape in agenda_slide.shapes if getattr(shape, "has_table", False)]
    assert tables, "テーブルが描画されていること"
    images = [shape for shape in agenda_slide.shapes if shape.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert images, "画像が描画されていること"

    kpi_slide = presentation.slides[2]
    charts = [shape for shape in kpi_slide.shapes if getattr(shape, "has_chart", False)]
    assert charts, "チャートが描画されていること"


def test_cli_run_supports_template(tmp_path) -> None:
    spec_path = Path("samples/sample_spec.json")
    workdir = tmp_path / "work-template"
    template_path = tmp_path / "template.pptx"

    template = Presentation()
    template.save(template_path)

    spec = JobSpec.parse_file(spec_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--template",
            str(template_path),
            "--output",
            "with-template.pptx",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    outputs_dir = workdir / "outputs"
    pptx_path = outputs_dir / "with-template.pptx"
    analysis_path = outputs_dir / "analysis.json"
    audit_path = outputs_dir / "audit_log.json"
    assert pptx_path.exists()
    assert analysis_path.exists()
    assert audit_path.exists()

    presentation = Presentation(pptx_path)
    assert len(presentation.slides) == len(spec.slides)

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert isinstance(audit_payload.get("refiner_adjustments"), list)

    for slide_spec, slide in zip(spec.slides, presentation.slides, strict=False):
        if slide_spec.title is None:
            continue
        actual = slide.shapes.title.text if slide.shapes.title else None
        assert actual == slide_spec.title

    agenda_slide = presentation.slides[1]
    tables = [shape for shape in agenda_slide.shapes if getattr(shape, "has_table", False)]
    assert tables


def test_cli_run_exports_pdf(tmp_path, monkeypatch) -> None:
    spec_path = Path("samples/sample_spec.json")
    workdir = tmp_path / "work-pdf"

    def fake_which(cmd: str) -> str | None:
        if cmd == "soffice":
            return "/usr/bin/soffice"
        return None

    def fake_run(command, check, stdout, stderr, timeout):  # noqa: ANN001
        outdir = Path(command[command.index("--outdir") + 1])
        pptx_input = Path(command[-1])
        pdf_path = outdir / f"{pptx_input.stem}.pdf"
        pdf_path.write_text("PDF", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(pdf_exporter, "shutil", shutil)
    monkeypatch.setattr(pdf_exporter.shutil, "which", fake_which)
    monkeypatch.setattr(pdf_exporter.subprocess, "run", fake_run)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--export-pdf",
            "--pdf-output",
            "custom.pdf",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    outputs_dir = workdir / "outputs"
    pptx_path = outputs_dir / "proposal.pptx"
    pdf_path = outputs_dir / "custom.pdf"
    audit_path = outputs_dir / "audit_log.json"

    assert pptx_path.exists()
    assert pdf_path.exists()
    assert audit_path.exists()

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    pdf_meta = audit_payload.get("pdf_export")
    assert pdf_meta is not None
    assert pdf_meta.get("attempts") == 1
    assert pdf_meta.get("converter") == "libreoffice"
    assert isinstance(audit_payload.get("refiner_adjustments"), list)


def test_cli_run_pdf_only(tmp_path, monkeypatch) -> None:
    spec_path = Path("samples/sample_spec.json")
    workdir = tmp_path / "work-pdf-only"

    def fake_which(cmd: str) -> str | None:
        if cmd == "soffice":
            return "/usr/bin/soffice"
        return None

    def fake_run(command, check, stdout, stderr, timeout):  # noqa: ANN001
        outdir = Path(command[command.index("--outdir") + 1])
        pptx_input = Path(command[-1])
        pdf_path = outdir / f"{pptx_input.stem}.pdf"
        pdf_path.write_text("PDF", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(pdf_exporter, "shutil", shutil)
    monkeypatch.setattr(pdf_exporter.shutil, "which", fake_which)
    monkeypatch.setattr(pdf_exporter.subprocess, "run", fake_run)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--export-pdf",
            "--pdf-mode",
            "only",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    outputs_dir = workdir / "outputs"
    pdf_path = outputs_dir / "proposal.pdf"
    pptx_path = outputs_dir / "proposal.pptx"
    audit_path = outputs_dir / "audit_log.json"

    assert pdf_path.exists()
    assert not pptx_path.exists()
    assert audit_path.exists()

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit_payload.get("artifacts", {}).get("pptx") is None
    assert audit_payload.get("artifacts", {}).get("pdf") == str(pdf_path)


def test_cli_run_pdf_skip_env(tmp_path, monkeypatch) -> None:
    spec_path = Path("samples/sample_spec.json")
    workdir = tmp_path / "work-pdf-skip"

    def fail_run(*args, **kwargs):  # noqa: ANN401
        raise AssertionError("LibreOffice should not be invoked when skip env is set")

    monkeypatch.setenv("PPTXGEN_SKIP_PDF_CONVERT", "1")
    monkeypatch.setattr(pdf_exporter.subprocess, "run", fail_run)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--export-pdf",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    outputs_dir = workdir / "outputs"
    pdf_path = outputs_dir / "proposal.pdf"
    audit_path = outputs_dir / "audit_log.json"
    assert pdf_path.exists()
    assert pdf_path.read_bytes() == b""
    assert audit_path.exists()

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit_payload.get("pdf_export", {}).get("converter") == "skipped"
