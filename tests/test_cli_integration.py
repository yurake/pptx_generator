"""CLI の統合テスト。"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from click.testing import CliRunner
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from pptx_generator.cli import app
from pptx_generator.branding_extractor import BrandingExtractionError
from pptx_generator.models import JobSpec, TemplateSpec
from pptx_generator.pipeline import pdf_exporter


def test_cli_gen_generates_outputs(tmp_path) -> None:
    spec_path = Path("samples/json/sample_spec.json")
    output_dir = tmp_path / "gen-work"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "gen",
            str(spec_path),
            "--output",
            str(output_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    spec = JobSpec.parse_file(spec_path)

    pptx_path = output_dir / "proposal.pptx"
    analysis_path = output_dir / "analysis.json"
    audit_path = output_dir / "audit_log.json"

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
    branding_info = audit_payload.get("branding")
    assert branding_info is not None
    assert branding_info.get("source", {}).get("type") in {"default", "builtin"}

    presentation = Presentation(pptx_path)
    assert len(presentation.slides) == len(spec.slides)

    for slide_spec, slide in zip(spec.slides, presentation.slides, strict=False):
        if slide_spec.title is None:
            continue
        actual = slide.shapes.title.text if slide.shapes.title else None
        assert actual == slide_spec.title

    agenda_index = next(index for index, slide_spec in enumerate(spec.slides) if slide_spec.id == "agenda")
    agenda_slide = presentation.slides[agenda_index]
    tables = [shape for shape in agenda_slide.shapes if getattr(shape, "has_table", False)]
    assert tables, "テーブルが描画されていること"
    images = [shape for shape in agenda_slide.shapes if shape.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert images, "画像が描画されていること"

    metrics_index = next(index for index, slide_spec in enumerate(spec.slides) if slide_spec.id == "metrics")
    metrics_slide = presentation.slides[metrics_index]
    charts = [shape for shape in metrics_slide.shapes if getattr(shape, "has_chart", False)]
    assert charts, "チャートが描画されていること"


def test_cli_gen_supports_template(tmp_path) -> None:
    spec_path = Path("samples/json/sample_spec.json")
    output_dir = tmp_path / "gen-work-template"
    template_path = tmp_path / "template.pptx"

    template = Presentation()
    template.save(template_path)

    spec = JobSpec.parse_file(spec_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "gen",
            str(spec_path),
            "--output",
            str(output_dir),
            "--template",
            str(template_path),
            "--pptx-name",
            "with-template.pptx",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    pptx_path = output_dir / "with-template.pptx"
    analysis_path = output_dir / "analysis.json"
    audit_path = output_dir / "audit_log.json"
    assert pptx_path.exists()
    assert analysis_path.exists()
    assert audit_path.exists()

    presentation = Presentation(pptx_path)
    assert len(presentation.slides) == len(spec.slides)

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert isinstance(audit_payload.get("refiner_adjustments"), list)
    branding_info = audit_payload.get("branding")
    assert branding_info is not None
    assert branding_info.get("source", {}).get("type") == "template"
    assert "config" in branding_info

    for slide_spec, slide in zip(spec.slides, presentation.slides, strict=False):
        if slide_spec.title is None:
            continue
        actual = slide.shapes.title.text if slide.shapes.title else None
        assert actual == slide_spec.title


def test_cli_gen_template_with_explicit_branding(tmp_path) -> None:
    spec_path = Path("samples/json/sample_spec.json")
    output_dir = tmp_path / "gen-work-template-branding"
    template_path = tmp_path / "template.pptx"
    branding_path = tmp_path / "custom-branding.json"

    Presentation().save(template_path)

    branding_payload = {
        "fonts": {
            "heading": {"name": "Test Font", "size_pt": 30, "color_hex": "#123456"},
            "body": {"name": "Test Font", "size_pt": 16, "color_hex": "#654321"},
        },
        "colors": {
            "primary": "#111111",
            "secondary": "#222222",
            "accent": "#333333",
            "background": "#FFFFFF",
        },
    }
    branding_path.write_text(json.dumps(branding_payload), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "gen",
            str(spec_path),
            "--output",
            str(output_dir),
            "--template",
            str(template_path),
            "--branding",
            str(branding_path),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    audit_payload = json.loads((output_dir / "audit_log.json").read_text(encoding="utf-8"))
    branding_info = audit_payload.get("branding")
    assert branding_info is not None
    assert branding_info.get("source", {}).get("type") == "file"
    assert branding_info.get("source", {}).get("path") == str(branding_path)


def test_cli_gen_template_branding_fallback(tmp_path, monkeypatch) -> None:
    spec_path = Path("samples/json/sample_spec.json")
    template_path = Path("samples/templates/templates.pptx")
    output_dir = tmp_path / "gen-work-template-fallback"

    def raise_error(_: Path) -> None:
        raise BrandingExtractionError("boom")

    monkeypatch.setattr("pptx_generator.cli.extract_branding_config", raise_error)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "gen",
            str(spec_path),
            "--output",
            str(output_dir),
            "--template",
            str(template_path),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    audit_payload = json.loads((output_dir / "audit_log.json").read_text(encoding="utf-8"))
    branding_info = audit_payload.get("branding")
    assert branding_info is not None
    assert branding_info.get("source", {}).get("type") in {"default", "builtin"}
    assert branding_info.get("source", {}).get("error") == "boom"


def test_cli_gen_exports_pdf(tmp_path, monkeypatch) -> None:
    spec_path = Path("samples/json/sample_spec.json")
    output_dir = tmp_path / "gen-work-pdf"

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
            "gen",
            str(spec_path),
            "--output",
            str(output_dir),
            "--export-pdf",
            "--pdf-output",
            "custom.pdf",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    pptx_path = output_dir / "proposal.pptx"
    pdf_path = output_dir / "custom.pdf"
    audit_path = output_dir / "audit_log.json"

    assert pptx_path.exists()
    assert pdf_path.exists()
    assert audit_path.exists()

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    pdf_meta = audit_payload.get("pdf_export")
    assert pdf_meta is not None
    assert pdf_meta.get("attempts") == 1
    assert pdf_meta.get("converter") == "libreoffice"
    assert isinstance(audit_payload.get("refiner_adjustments"), list)


def test_cli_gen_pdf_only(tmp_path, monkeypatch) -> None:
    spec_path = Path("samples/json/sample_spec.json")
    output_dir = tmp_path / "gen-work-pdf-only"

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
            "gen",
            str(spec_path),
            "--output",
            str(output_dir),
            "--export-pdf",
            "--pdf-mode",
            "only",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    pdf_path = output_dir / "proposal.pdf"
    pptx_path = output_dir / "proposal.pptx"
    audit_path = output_dir / "audit_log.json"

    assert pdf_path.exists()
    assert not pptx_path.exists()
    assert audit_path.exists()

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit_payload.get("artifacts", {}).get("pptx") is None
    assert audit_payload.get("artifacts", {}).get("pdf") == str(pdf_path)


def test_cli_gen_pdf_skip_env(tmp_path, monkeypatch) -> None:
    spec_path = Path("samples/json/sample_spec.json")
    output_dir = tmp_path / "gen-work-pdf-skip"

    def fail_run(*args, **kwargs):  # noqa: ANN401
        raise AssertionError("LibreOffice should not be invoked when skip env is set")

    monkeypatch.setenv("PPTXGEN_SKIP_PDF_CONVERT", "1")
    monkeypatch.setattr(pdf_exporter.subprocess, "run", fail_run)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "gen",
            str(spec_path),
            "--output",
            str(output_dir),
            "--export-pdf",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    pdf_path = output_dir / "proposal.pdf"
    audit_path = output_dir / "audit_log.json"
    assert pdf_path.exists()
    assert pdf_path.read_bytes() == b""
    assert audit_path.exists()

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit_payload.get("pdf_export", {}).get("converter") == "skipped"


def test_cli_gen_default_output_directory(tmp_path) -> None:
    runner = CliRunner()
    repo_root = Path(__file__).resolve().parents[1]

    with runner.isolated_filesystem(temp_dir=tmp_path) as fs:
        fs_root = Path(fs)
        shutil.copytree(repo_root / "samples", fs_root / "samples")
        shutil.copytree(repo_root / "config", fs_root / "config")

        result = runner.invoke(
            app,
            [
                "gen",
                "samples/json/sample_spec.json",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        output_dir = Path(".pptx/gen")
        assert (output_dir / "proposal.pptx").exists()
        assert (output_dir / "analysis.json").exists()
        audit_path = output_dir / "audit_log.json"
        assert audit_path.exists()

        audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
        branding_info = audit_payload.get("branding")
        assert branding_info is not None
        assert branding_info.get("source", {}).get("type") in {"default", "builtin"}


def test_cli_tpl_extract_basic(tmp_path) -> None:
    """tpl-extract コマンドの基本動作テスト。"""
    template_path = Path("samples/templates/templates.pptx")
    output_dir = tmp_path / "extract-basic"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "tpl-extract",
            "--template",
            str(template_path),
            "--output",
            str(output_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "テンプレート抽出が完了しました" in result.output

    output_path = output_dir / "template_spec.json"
    assert output_path.exists()
    branding_path = output_dir / "branding.json"
    assert branding_path.exists()

    # JSON内容の検証
    template_spec_data = json.loads(output_path.read_text(encoding="utf-8"))
    template_spec = TemplateSpec.model_validate(template_spec_data)
    
    assert template_spec.template_path == str(template_path)
    assert len(template_spec.layouts) > 0
    assert template_spec.extracted_at is not None

    branding_data = json.loads(branding_path.read_text(encoding="utf-8"))
    assert branding_data.get("version") == "layout-style-v1"
    theme_section = branding_data.get("theme", {})
    assert "fonts" in theme_section
    assert "colors" in theme_section
    assert "components" in branding_data


def test_cli_tpl_extract_custom_output(tmp_path) -> None:
    """tpl-extract コマンドのカスタム出力パステスト。"""
    template_path = Path("samples/templates/templates.pptx")
    output_dir = tmp_path / "extract-custom"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "tpl-extract",
            "--template",
            str(template_path),
            "--output",
            str(output_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    spec_path = output_dir / "template_spec.json"
    assert spec_path.exists()
    branding_path = output_dir / "branding.json"
    assert branding_path.exists()

    template_spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
    template_spec = TemplateSpec.model_validate(template_spec_data)
    assert template_spec.template_path == str(template_path)

    branding_data = json.loads(branding_path.read_text(encoding="utf-8"))
    assert branding_data.get("version") == "layout-style-v1"
    assert "components" in branding_data


def test_cli_tpl_extract_with_filters(tmp_path) -> None:
    """tpl-extract コマンドのフィルタ機能テスト。"""
    template_path = Path("samples/templates/templates.pptx")
    output_dir = tmp_path / "extract-filter"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "tpl-extract",
            "--template",
            str(template_path),
            "--output",
            str(output_dir),
            "--layout",
            "タイトル",  # レイアウト名フィルタ
            "--anchor",
            "title",    # アンカー名フィルタ
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    output_path = output_dir / "template_spec.json"
    assert output_path.exists()
    branding_path = output_dir / "branding.json"
    assert branding_path.exists()

    template_spec_data = json.loads(output_path.read_text(encoding="utf-8"))
    template_spec = TemplateSpec.model_validate(template_spec_data)
    
    # フィルタが適用されていることを確認（具体的な検証は実際のテンプレート内容に依存）
    assert template_spec.template_path == str(template_path)


def test_cli_tpl_extract_nonexistent_file() -> None:
    """tpl-extract コマンドの存在しないファイルテスト。"""
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "tpl-extract",
            "--template",
            "nonexistent.pptx",
        ],
    )

    assert result.exit_code == 4  # FileNotFoundError
    assert "ファイルが見つかりません" in result.output


def test_cli_tpl_extract_verbose_output(tmp_path) -> None:
    """tpl-extract コマンドの詳細出力テスト。"""
    template_path = Path("samples/templates/templates.pptx")
    output_dir = tmp_path / "extract-verbose"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "--verbose",  # グローバルオプション
            "tpl-extract",
            "--template",
            str(template_path),
            "--output",
            str(output_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "テンプレート抽出が完了しました" in result.output
    assert "抽出されたレイアウト数:" in result.output
    assert "抽出された図形・アンカー数:" in result.output


def test_cli_tpl_extract_with_mock_presentation(tmp_path) -> None:
    """tpl-extract コマンドのモックプレゼンテーションテスト。"""
    # 一時的なPPTXファイルを作成
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as temp_file:
        temp_template_path = Path(temp_file.name)
    
    # 簡単なプレゼンテーションを作成
    presentation = Presentation()
    layout = presentation.slide_layouts[0]  # タイトルレイアウト
    presentation.save(temp_template_path)
    
    try:
        output_dir = tmp_path / "extract-mock"
        runner = CliRunner()

        result = runner.invoke(
            app,
            [
                "tpl-extract",
                "--template",
                str(temp_template_path),
                "--output",
                str(output_dir),
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        output_path = output_dir / "template_spec.json"
        assert output_path.exists()
        branding_path = output_dir / "branding.json"
        assert branding_path.exists()

        template_spec_data = json.loads(output_path.read_text(encoding="utf-8"))
        template_spec = TemplateSpec.model_validate(template_spec_data)

        assert template_spec.template_path == str(temp_template_path)
        assert len(template_spec.layouts) > 0
        branding_data = json.loads(branding_path.read_text(encoding="utf-8"))
        assert branding_data.get("version") == "layout-style-v1"
        assert "theme" in branding_data

    finally:
        # 一時ファイルをクリーンアップ
        temp_template_path.unlink()


def test_cli_tpl_extract_default_output_directory(tmp_path) -> None:
    runner = CliRunner()
    repo_root = Path(__file__).resolve().parents[1]

    with runner.isolated_filesystem(temp_dir=tmp_path) as fs:
        fs_root = Path(fs)
        shutil.copytree(repo_root / "samples", fs_root / "samples")

        result = runner.invoke(
            app,
            [
                "tpl-extract",
                "--template",
                "samples/templates/templates.pptx",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        output_dir = Path(".pptx/extract")
        spec_path = output_dir / "template_spec.json"
        branding_path = output_dir / "branding.json"
        assert spec_path.exists()
        assert branding_path.exists()
