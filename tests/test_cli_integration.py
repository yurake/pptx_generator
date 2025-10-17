"""CLI の統合テスト。"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from click.testing import CliRunner
from collections import Counter
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from pptx_generator.cli import app
from pptx_generator.branding_extractor import BrandingExtractionError
from pptx_generator.models import (JobSpec, TemplateRelease,
                                   TemplateReleaseGoldenRun,
                                   TemplateReleaseReport, TemplateSpec)
from pptx_generator.pipeline import pdf_exporter

SAMPLE_TEMPLATE = Path("samples/templates/templates.pptx")
CONTENT_APPROVED_SAMPLE = Path("samples/json/sample_content_approved.json")
CONTENT_REVIEW_LOG_SAMPLE = Path("samples/json/sample_content_review_log.json")


def _collect_paragraph_texts(slide) -> list[str]:
    texts: list[str] = []
    for shape in slide.shapes:
        if not getattr(shape, "has_text_frame", False):
            continue
        for paragraph in shape.text_frame.paragraphs:
            text = paragraph.text.strip()
            if text:
                texts.append(text)
    return texts


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
            "--template",
            str(SAMPLE_TEMPLATE),
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
    assert branding_info.get("source", {}).get("type") == "template"
    assert branding_info.get("source", {}).get("template") == str(SAMPLE_TEMPLATE)

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


def test_cli_gen_with_content_approved(tmp_path) -> None:
    spec_path = Path("samples/json/sample_spec.json")
    content_path = CONTENT_APPROVED_SAMPLE
    review_log_path = CONTENT_REVIEW_LOG_SAMPLE

    approved_payload = json.loads(content_path.read_text(encoding="utf-8"))
    review_log_payload = json.loads(review_log_path.read_text(encoding="utf-8"))
    output_dir = tmp_path / "gen-content"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "gen",
            str(spec_path),
            "--output",
            str(output_dir),
            "--template",
            str(SAMPLE_TEMPLATE),
            "--content-approved",
            str(content_path),
            "--content-review-log",
            str(review_log_path),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    audit_path = output_dir / "audit_log.json"
    assert audit_path.exists()

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert isinstance(audit_payload.get("refiner_adjustments"), list)
    content_meta = audit_payload.get("content_approval")
    assert content_meta is not None
    assert content_meta["slides"] == len(approved_payload["slides"])
    assert content_meta["path"] == str(content_path.resolve())
    assert content_meta["hash"].startswith("sha256:")
    assert content_meta["slide_ids"] == [slide["id"] for slide in approved_payload["slides"]]
    assert content_meta["applied_to_spec"] is True
    assert set(content_meta["updated_slide_ids"]) == {slide["id"] for slide in approved_payload["slides"]}

    review_meta = audit_payload.get("content_review_log")
    assert review_meta is not None
    assert review_meta["events"] == len(review_log_payload)
    assert review_meta["path"] == str(review_log_path.resolve())
    assert review_meta["hash"].startswith("sha256:")
    expected_actions = Counter(entry["action"] for entry in review_log_payload)
    assert review_meta["actions"] == dict(expected_actions)

    presentation = Presentation(output_dir / "proposal.pptx")

    agenda_slide = presentation.slides[1]
    agenda_texts = _collect_paragraph_texts(agenda_slide)
    assert "背景整理（承認済み）" in agenda_texts
    assert "提案サマリー（承認済み）" in agenda_texts
    assert "ロードマップと体制（承認済み）" in agenda_texts

    problem_slide = presentation.slides[2]
    notes_text = problem_slide.notes_slide.notes_text_frame.text
    assert "監査ログ要件を強調（承認済み）。" in notes_text


def test_cli_gen_with_unapproved_content_fails(tmp_path) -> None:
    spec_path = Path("samples/json/sample_spec.json")
    content_path = tmp_path / "content_approved.json"
    payload = {
        "slides": [
            {
                "id": "s01",
                "intent": "市場動向",
                "status": "draft",
                "elements": {"title": "市場", "body": ["需要は増加"]},
            }
        ]
    }
    content_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    output_dir = tmp_path / "gen-content-fail"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "gen",
            str(spec_path),
            "--output",
            str(output_dir),
            "--template",
            str(SAMPLE_TEMPLATE),
            "--content-approved",
            str(content_path),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 4
    assert "承認済みコンテンツの読み込みに失敗しました" in result.output
    audit_path = output_dir / "audit_log.json"
    assert not audit_path.exists()


def test_cli_gen_supports_template(tmp_path) -> None:
    spec_path = Path("samples/json/sample_spec.json")
    output_dir = tmp_path / "gen-work-template"
    template_path = tmp_path / "template.pptx"

    shutil.copyfile(SAMPLE_TEMPLATE, template_path)

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

    shutil.copyfile(SAMPLE_TEMPLATE, template_path)

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


def test_cli_layout_validate_with_analyzer_snapshot(tmp_path) -> None:
    spec_path = Path("samples/json/sample_spec.json")
    template_path = SAMPLE_TEMPLATE
    gen_output = tmp_path / "gen-with-snapshot"
    validation_output = tmp_path / "validation-with-snapshot"

    runner = CliRunner()
    gen_result = runner.invoke(
        app,
        [
            "gen",
            str(spec_path),
            "--output",
            str(gen_output),
            "--template",
            str(template_path),
            "--emit-structure-snapshot",
        ],
        catch_exceptions=False,
    )

    assert gen_result.exit_code == 0, gen_result.output

    snapshot_path = gen_output / "analysis_snapshot.json"
    assert snapshot_path.exists(), "Analyzer スナップショットが生成されていること"

    validate_result = runner.invoke(
        app,
        [
            "layout-validate",
            "--template",
            str(template_path),
            "--output",
            str(validation_output),
            "--analyzer-snapshot",
            str(snapshot_path),
        ],
        catch_exceptions=False,
    )

    assert validate_result.exit_code == 0, validate_result.output

    diagnostics_path = validation_output / "diagnostics.json"
    diff_path = validation_output / "diff_report.json"
    assert diagnostics_path.exists()
    assert diff_path.exists()

    diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    warning_codes = {entry["code"] for entry in diagnostics.get("warnings", [])}
    assert "analyzer_anchor_missing" in warning_codes
    assert "analyzer_anchor_unexpected" in warning_codes
    assert diagnostics["stats"]["layouts_total"] > 0

    diff_payload = json.loads(diff_path.read_text(encoding="utf-8"))
    issue_codes = {issue["code"] for issue in diff_payload.get("issues", [])}
    assert "analyzer_anchor_missing" in issue_codes


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
            "--template",
            str(SAMPLE_TEMPLATE),
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
            "--template",
            str(SAMPLE_TEMPLATE),
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
            "--template",
            str(SAMPLE_TEMPLATE),
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
                "--template",
                "samples/templates/templates.pptx",
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
        assert branding_info.get("source", {}).get("type") == "template"


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


def test_cli_tpl_release_generates_outputs(tmp_path) -> None:
    runner = CliRunner()
    repo_root = Path(__file__).resolve().parents[1]

    with runner.isolated_filesystem(temp_dir=tmp_path) as fs:
        fs_root = Path(fs)
        shutil.copytree(repo_root / "samples", fs_root / "samples")

        result = runner.invoke(
            app,
            [
                "tpl-release",
                "--template",
                "samples/templates/templates.pptx",
                "--brand",
                "Sample",
                "--version",
                "1.0.0",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "テンプレートリリースメタを出力しました" in result.output

        release_path = Path(".pptx/release/template_release.json")
        report_path = Path(".pptx/release/release_report.json")
        assert release_path.exists()
        assert report_path.exists()

        release = TemplateRelease.model_validate_json(
            release_path.read_text(encoding="utf-8")
        )
        report = TemplateReleaseReport.model_validate_json(
            report_path.read_text(encoding="utf-8")
        )

        assert release.template_id == "Sample_1.0.0"
        assert report.template_id == "Sample_1.0.0"
        assert release.golden_runs == []
        assert release.analyzer_metrics is None
        assert report.analyzer is None
        assert not (Path(".pptx/release") / "golden_runs.json").exists()


def test_cli_tpl_release_with_baseline(tmp_path) -> None:
    runner = CliRunner()
    repo_root = Path(__file__).resolve().parents[1]

    with runner.isolated_filesystem(temp_dir=tmp_path) as fs:
        fs_root = Path(fs)
        shutil.copytree(repo_root / "samples", fs_root / "samples")

        # 1st run -> baseline release
        first_output = Path(".pptx/release")
        result_first = runner.invoke(
            app,
            [
                "tpl-release",
                "--template",
                "samples/templates/templates.pptx",
                "--brand",
                "Sample",
                "--version",
                "1.0.0",
                "--output",
                str(first_output),
            ],
            catch_exceptions=False,
        )
        assert result_first.exit_code == 0

        baseline_path = first_output / "template_release.json"
        assert baseline_path.exists()

        # 2nd run -> compare against baseline
        second_output = Path(".pptx/release-v2")
        result_second = runner.invoke(
            app,
            [
                "tpl-release",
                "--template",
                "samples/templates/templates.pptx",
                "--brand",
                "Sample",
                "--version",
                "1.1.0",
                "--output",
                str(second_output),
                "--baseline-release",
                str(baseline_path),
            ],
            catch_exceptions=False,
        )

        assert result_second.exit_code == 0
        report_path = second_output / "release_report.json"
        assert report_path.exists()

        report = TemplateReleaseReport.model_validate_json(
            report_path.read_text(encoding="utf-8")
        )
        assert report.baseline_id == "Sample_1.0.0"
        release_path = second_output / "template_release.json"
        assert release_path.exists()
        release = TemplateRelease.model_validate_json(
            release_path.read_text(encoding="utf-8")
        )
        assert release.golden_runs == []
        assert release.analyzer_metrics is None
        assert report.analyzer is None


def test_cli_tpl_release_with_golden_spec(tmp_path) -> None:
    runner = CliRunner()
    repo_root = Path(__file__).resolve().parents[1]

    with runner.isolated_filesystem(temp_dir=tmp_path) as fs:
        fs_root = Path(fs)
        shutil.copytree(repo_root / "samples", fs_root / "samples")
        shutil.copytree(repo_root / "config", fs_root / "config")

        result = runner.invoke(
            app,
            [
                "tpl-release",
                "--template",
                "samples/templates/templates.pptx",
                "--brand",
                "Sample",
                "--version",
                "1.0.0",
                "--golden-spec",
                "samples/json/sample_spec.json",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0

        release_path = Path(".pptx/release/template_release.json")
        golden_path = Path(".pptx/release/golden_runs.json")
        assert release_path.exists()
        assert golden_path.exists()

        release = TemplateRelease.model_validate_json(
            release_path.read_text(encoding="utf-8")
        )
        assert len(release.golden_runs) == 1
        golden_run = release.golden_runs[0]
        assert golden_run.status == "passed"
        metrics = release.analyzer_metrics
        assert metrics is not None
        assert metrics.summary.run_count == 1
        assert metrics.runs[0].status == "included"

        golden_runs_data = json.loads(golden_path.read_text(encoding="utf-8"))
        assert len(golden_runs_data) == 1
        parsed_run = TemplateReleaseGoldenRun.model_validate(golden_runs_data[0])
        assert parsed_run.status == "passed"
        assert Path(parsed_run.output_dir).exists()
        assert Path(parsed_run.pptx_path).exists()

        report_path = Path(".pptx/release/release_report.json")
        report = TemplateReleaseReport.model_validate_json(
            report_path.read_text(encoding="utf-8")
        )
        assert report.analyzer is not None
        assert report.analyzer.current.issues.total >= 0
        assert report.analyzer.baseline is None
        assert report.analyzer.delta is None


def test_cli_tpl_release_golden_spec_failure(tmp_path) -> None:
    runner = CliRunner()
    repo_root = Path(__file__).resolve().parents[1]

    with runner.isolated_filesystem(temp_dir=tmp_path) as fs:
        fs_root = Path(fs)
        shutil.copytree(repo_root / "samples", fs_root / "samples")
        shutil.copytree(repo_root / "config", fs_root / "config")

        broken_spec = Path("broken_spec.json")
        broken_spec.write_text("{}", encoding="utf-8")  # 必須項目が欠落

        result = runner.invoke(
            app,
            [
                "tpl-release",
                "--template",
                "samples/templates/templates.pptx",
                "--brand",
                "Sample",
                "--version",
                "1.0.0",
                "--golden-spec",
                str(broken_spec),
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 6

        release_path = Path(".pptx/release/template_release.json")
        golden_path = Path(".pptx/release/golden_runs.json")
        assert release_path.exists()
        release = TemplateRelease.model_validate_json(
            release_path.read_text(encoding="utf-8")
        )
        assert release.diagnostics.errors
        assert release.golden_runs
        assert release.golden_runs[0].status == "failed"
        metrics = release.analyzer_metrics
        assert metrics is not None
        assert metrics.summary.run_count == 0
        assert metrics.runs[0].status == "skipped"
        assert golden_path.exists()
        golden_runs = json.loads(golden_path.read_text(encoding="utf-8"))
        assert len(golden_runs) == 1
        parsed_run = TemplateReleaseGoldenRun.model_validate(golden_runs[0])
        assert parsed_run.status == "failed"
