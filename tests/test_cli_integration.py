"""CLI の統合テスト。"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from click.testing import CliRunner
from collections import Counter
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from pptx_generator.cli import app
from pptx_generator.branding_extractor import BrandingExtractionError
from pptx_generator.models import (JobSpec, JobSpecScaffold, TemplateRelease,
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


def _prepare_generate_ready(
    runner: CliRunner,
    spec_path: Path,
    mapping_dir: Path,
    *,
    draft_dir: Path | None = None,
    extra_args: list[str] | None = None,
) -> Path:
    args = [
        "mapping",
        str(spec_path),
        "--output",
        str(mapping_dir),
        "--template",
        str(SAMPLE_TEMPLATE),
    ]
    if draft_dir is not None:
        args.extend(["--draft-output", str(draft_dir)])
    if extra_args:
        args.extend(extra_args)

    result = runner.invoke(app, args, catch_exceptions=False)
    assert result.exit_code == 0

    generate_ready_path = mapping_dir / "generate_ready.json"
    assert generate_ready_path.exists()
    return generate_ready_path


def test_cli_gen_renders_generate_ready(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    mapping_dir = tmp_path / "mapping"
    draft_dir = tmp_path / "draft"
    output_dir = tmp_path / "gen-work"
    runner = CliRunner()

    generate_ready_path = _prepare_generate_ready(
        runner,
        spec_path,
        mapping_dir,
        draft_dir=draft_dir,
    )

    result = runner.invoke(
        app,
        [
            "gen",
            str(generate_ready_path),
            "--output",
            str(output_dir),
            "--template",
            str(SAMPLE_TEMPLATE),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    pptx_path = output_dir / "proposal.pptx"
    analysis_path = output_dir / "analysis.json"
    audit_path = output_dir / "audit_log.json"

    assert pptx_path.exists()
    assert analysis_path.exists()
    assert audit_path.exists()

    spec = JobSpec.parse_file(spec_path)
    payload = json.loads(analysis_path.read_text(encoding="utf-8"))
    assert payload.get("slides") == len(spec.slides)

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    hashes = audit_payload.get("hashes")
    assert isinstance(hashes, dict)
    assert hashes.get("generate_ready", "").startswith("sha256:")
    assert hashes.get("pptx", "").startswith("sha256:")
    assert hashes.get("analysis", "").startswith("sha256:")

    presentation = Presentation(pptx_path)
    assert len(presentation.slides) == len(spec.slides)


def test_cli_gen_requires_export_for_pdf_mode(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    mapping_dir = tmp_path / "mapping"
    runner = CliRunner()

    generate_ready_path = _prepare_generate_ready(runner, spec_path, mapping_dir)

    result = runner.invoke(
        app,
        [
            "gen",
            str(generate_ready_path),
            "--template",
            str(SAMPLE_TEMPLATE),
            "--pdf-mode",
            "only",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 2
    assert "--pdf-mode" in result.output


def test_cli_gen_allows_custom_output_name(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    mapping_dir = tmp_path / "mapping"
    output_dir = tmp_path / "custom"
    runner = CliRunner()

    generate_ready_path = _prepare_generate_ready(runner, spec_path, mapping_dir)

    result = runner.invoke(
        app,
        [
            "gen",
            str(generate_ready_path),
            "--output",
            str(output_dir),
            "--template",
            str(SAMPLE_TEMPLATE),
            "--pptx-name",
            "deck.pptx",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert (output_dir / "deck.pptx").exists()


def test_cli_gen_missing_generate_ready_path_fails(tmp_path) -> None:
    runner = CliRunner()
    missing_path = tmp_path / "not-found.json"

    result = runner.invoke(
        app,
        [
            "gen",
            str(missing_path),
            "--template",
            str(SAMPLE_TEMPLATE),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 2
    assert "GENERATE_READY_PATH" in result.output


def test_cli_content_ai_generation(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    output_dir = tmp_path / "content-ai"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "content",
            str(spec_path),
            "--ai-policy-id",
            "proposal-default",
            "--output",
            str(output_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    draft_path = output_dir / "content_draft.json"
    meta_path = output_dir / "ai_generation_meta.json"
    log_path = output_dir / "content_ai_log.json"

    assert draft_path.exists()
    assert meta_path.exists()
    assert log_path.exists()

    draft_payload = json.loads(draft_path.read_text(encoding="utf-8"))
    meta_payload = json.loads(meta_path.read_text(encoding="utf-8"))
    log_payload = json.loads(log_path.read_text(encoding="utf-8"))

    assert "slides" in draft_payload
    assert meta_payload["policy_id"] == "proposal-default"
    assert len(log_payload) == len(draft_payload["slides"])




def test_cli_mapping_then_render(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    mapping_dir = tmp_path / "mapping"
    render_dir = tmp_path / "render"
    draft_dir = tmp_path / "draft"

    runner = CliRunner()

    mapping_result = runner.invoke(
        app,
        [
            "mapping",
            str(spec_path),
            "--output",
            str(mapping_dir),
            "--template",
            str(SAMPLE_TEMPLATE),
            "--draft-output",
            str(draft_dir),
        ],
        catch_exceptions=False,
    )

    assert mapping_result.exit_code == 0

    generate_ready_path = mapping_dir / "generate_ready.json"
    mapping_log_path = mapping_dir / "mapping_log.json"
    assert generate_ready_path.exists()
    assert mapping_log_path.exists()

    render_result = runner.invoke(
        app,
        [
            "render",
            str(generate_ready_path),
            "--output",
            str(render_dir),
            "--template",
            str(SAMPLE_TEMPLATE),
        ],
        catch_exceptions=False,
    )

    assert render_result.exit_code == 0

    audit_path = render_dir / "audit_log.json"
    assert audit_path.exists()
    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    hashes = audit_payload.get("hashes")
    assert hashes is not None
    assert hashes.get("generate_ready", "").startswith("sha256:")
    # mapping_log は別ディレクトリのため単体 render 実行ではハッシュ対象外
    assert hashes.get("mapping_log") is None
    artifacts = audit_payload.get("artifacts", {})
    assert artifacts.get("generate_ready") == str(generate_ready_path)














def test_cli_mapping_command_generates_outputs(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    output_dir = tmp_path / "mapping-work"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "mapping",
            str(spec_path),
            "--output",
            str(output_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    generate_ready_path = output_dir / "generate_ready.json"
    mapping_log_path = output_dir / "mapping_log.json"
    assert generate_ready_path.exists()
    assert mapping_log_path.exists()

    payload = json.loads(generate_ready_path.read_text(encoding="utf-8"))
    assert payload["meta"]["job_meta"]["title"] == "RM-043 拡張テンプレート検証"
    assert payload["meta"]["job_auth"]["created_by"] == "codex"


def test_cli_render_command_consumes_generate_ready(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    mapping_dir = tmp_path / "mapping-work"
    render_dir = tmp_path / "render-work"
    runner = CliRunner()

    mapping_result = runner.invoke(
        app,
        [
            "mapping",
            str(spec_path),
            "--output",
            str(mapping_dir),
            "--template",
            str(SAMPLE_TEMPLATE),
        ],
        catch_exceptions=False,
    )
    assert mapping_result.exit_code == 0

    generate_ready_path = mapping_dir / "generate_ready.json"
    assert generate_ready_path.exists()

    render_result = runner.invoke(
        app,
        [
            "render",
            str(generate_ready_path),
            "--output",
            str(render_dir),
            "--template",
            str(SAMPLE_TEMPLATE),
        ],
        catch_exceptions=False,
    )

    assert render_result.exit_code == 0

    pptx_path = render_dir / "proposal.pptx"
    audit_path = render_dir / "audit_log.json"
    assert pptx_path.exists()
    assert audit_path.exists()

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit_payload["artifacts"]["generate_ready"] == str(generate_ready_path)
    assert audit_payload["artifacts"]["rendering_log"].endswith("rendering_log.json")
    rendering_summary = audit_payload.get("rendering")
    assert rendering_summary is not None
    assert rendering_summary.get("warnings_total") >= 0
    spec = JobSpec.parse_file(spec_path)
    assert audit_payload["slides"] == len(spec.slides)


def test_cli_compose_generates_stage45_outputs(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    draft_dir = tmp_path / "compose-draft"
    compose_dir = tmp_path / "compose-gen"
    spec = JobSpec.parse_file(spec_path)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "compose",
            str(spec_path),
            "--draft-output",
            str(draft_dir),
            "--output",
            str(compose_dir),
            "--template",
            str(SAMPLE_TEMPLATE),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    draft_path = draft_dir / "draft_draft.json"
    approved_path = draft_dir / "draft_approved.json"
    log_path = draft_dir / "draft_review_log.json"
    meta_path = draft_dir / "draft_meta.json"
    assert draft_path.exists()
    assert approved_path.exists()
    assert log_path.exists()
    assert meta_path.exists()

    generate_ready_path = compose_dir / "generate_ready.json"
    mapping_log_path = compose_dir / "mapping_log.json"
    assert generate_ready_path.exists()
    assert mapping_log_path.exists()

    draft_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert draft_meta.get("slides") == len(spec.slides)

    mapping_payload = json.loads(generate_ready_path.read_text(encoding="utf-8"))
    assert mapping_payload["meta"]["job_meta"]["title"] == "RM-043 拡張テンプレート検証"


def test_cli_layout_validate_with_analyzer_snapshot(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    template_path = SAMPLE_TEMPLATE
    gen_output = tmp_path / "gen-with-snapshot"
    validation_output = tmp_path / "validation-with-snapshot"
    mapping_dir = tmp_path / "mapping-with-snapshot"

    runner = CliRunner()
    generate_ready_path = _prepare_generate_ready(runner, spec_path, mapping_dir)
    gen_result = runner.invoke(
        app,
        [
            "gen",
            str(generate_ready_path),
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
    jobspec_path = output_dir / "jobspec.json"
    assert jobspec_path.exists()

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

    jobspec_data = json.loads(jobspec_path.read_text(encoding="utf-8"))
    jobspec = JobSpecScaffold.model_validate(jobspec_data)
    assert jobspec.meta.template_path == str(template_path)

    layouts_path = output_dir / "layouts.jsonl"
    diagnostics_path = output_dir / "diagnostics.json"
    assert layouts_path.exists()
    assert diagnostics_path.exists()

    assert jobspec.slides, "少なくとも1件のスライドが出力されること"
    assert "ジョブスペック雛形を出力しました" in result.output
    assert "ジョブスペックのスライド数:" in result.output
    assert "Layouts:" in result.output
    assert "Diagnostics:" in result.output
    assert "検出結果: warnings=" in result.output


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
    jobspec_path = output_dir / "jobspec.json"
    assert jobspec_path.exists()

    template_spec_data = json.loads(spec_path.read_text(encoding="utf-8"))
    template_spec = TemplateSpec.model_validate(template_spec_data)
    assert template_spec.template_path == str(template_path)

    branding_data = json.loads(branding_path.read_text(encoding="utf-8"))
    assert branding_data.get("version") == "layout-style-v1"
    assert "components" in branding_data

    jobspec_data = json.loads(jobspec_path.read_text(encoding="utf-8"))
    jobspec = JobSpecScaffold.model_validate(jobspec_data)
    assert jobspec.meta.template_path == str(template_path)


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
    jobspec_path = output_dir / "jobspec.json"
    assert jobspec_path.exists()

    template_spec_data = json.loads(output_path.read_text(encoding="utf-8"))
    template_spec = TemplateSpec.model_validate(template_spec_data)
    
    # フィルタが適用されていることを確認（具体的な検証は実際のテンプレート内容に依存）
    assert template_spec.template_path == str(template_path)

    jobspec_data = json.loads(jobspec_path.read_text(encoding="utf-8"))
    jobspec = JobSpecScaffold.model_validate(jobspec_data)
    assert jobspec.meta.template_path == str(template_path)


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
    assert "ジョブスペックのスライド数:" in result.output
    assert "Layouts:" in result.output
    assert "Diagnostics:" in result.output


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
        jobspec_path = output_dir / "jobspec.json"
        assert jobspec_path.exists()

        template_spec_data = json.loads(output_path.read_text(encoding="utf-8"))
        template_spec = TemplateSpec.model_validate(template_spec_data)

        assert template_spec.template_path == str(temp_template_path)
        assert len(template_spec.layouts) > 0
        branding_data = json.loads(branding_path.read_text(encoding="utf-8"))
        assert branding_data.get("version") == "layout-style-v1"
        assert "theme" in branding_data

        jobspec_data = json.loads(jobspec_path.read_text(encoding="utf-8"))
        jobspec = JobSpecScaffold.model_validate(jobspec_data)
        assert jobspec.meta.template_path == str(temp_template_path)

        layouts_path = output_dir / "layouts.jsonl"
        diagnostics_path = output_dir / "diagnostics.json"
        assert layouts_path.exists()
        assert diagnostics_path.exists()
        assert "Layouts:" in result.output
        assert "Diagnostics:" in result.output

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
        jobspec_path = output_dir / "jobspec.json"
        layouts_path = output_dir / "layouts.jsonl"
        diagnostics_path = output_dir / "diagnostics.json"
        assert spec_path.exists()
        assert branding_path.exists()
        assert jobspec_path.exists()
        assert layouts_path.exists()
        assert diagnostics_path.exists()


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


def test_cli_tpl_release_reuses_baseline_golden_specs(tmp_path) -> None:
    runner = CliRunner()
    repo_root = Path(__file__).resolve().parents[1]

    with runner.isolated_filesystem(temp_dir=tmp_path) as fs:
        fs_root = Path(fs)
        shutil.copytree(repo_root / "samples", fs_root / "samples")
        shutil.copytree(repo_root / "config", fs_root / "config")

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
                "--golden-spec",
                "samples/json/sample_jobspec.json",
            ],
            catch_exceptions=False,
        )
        assert result_first.exit_code == 0
        baseline_path = first_output / "template_release.json"
        assert baseline_path.exists()

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

        release_path = second_output / "template_release.json"
        assert release_path.exists()
        release = TemplateRelease.model_validate_json(
            release_path.read_text(encoding="utf-8")
        )
        assert release.golden_runs
        assert any(
            run.spec_path.endswith("sample_jobspec.json") for run in release.golden_runs
        )
        metrics = release.analyzer_metrics
        assert metrics is not None
        assert metrics.summary.run_count >= 1

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
                "samples/json/sample_jobspec.json",
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
