"""CLI の統合テスト。"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from click.testing import CliRunner
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

from pptx_generator.cli import app
from pptx_generator.branding_extractor import BrandingExtractionError
from pptx_generator.layout_validation import LayoutValidationResult, LayoutValidationSuite
from pptx_generator.models import (JobSpec, JobSpecScaffold, TemplateRelease,
                                   TemplateReleaseGoldenRun,
                                   TemplateReleaseReport, TemplateSpec)
from pptx_generator.pipeline import pdf_exporter

SAMPLE_TEMPLATE = Path("samples/templates/templates.pptx")
BRIEF_SOURCE = Path("samples/contents/sample_import_content_summary.txt")


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


def _prepare_brief_inputs(runner: CliRunner, temp_dir: Path) -> dict[str, Path]:
    brief_dir = temp_dir / "brief-input"
    result = runner.invoke(
        app,
        [
            "content",
            str(BRIEF_SOURCE),
            "--output",
            str(brief_dir),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    return {
        "dir": brief_dir,
        "cards": brief_dir / "brief_cards.json",
        "log": brief_dir / "brief_log.json",
        "meta": brief_dir / "ai_generation_meta.json",
    }


def _brief_args(paths: dict[str, Path]) -> list[str]:
    return [
        "--brief-cards",
        str(paths["cards"]),
        "--brief-log",
        str(paths["log"]),
        "--brief-meta",
        str(paths["meta"]),
    ]


def test_cli_gen_generates_outputs(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    output_dir = tmp_path / "gen-work"
    runner = CliRunner()
    brief_paths = _prepare_brief_inputs(runner, tmp_path)

    result = runner.invoke(
        app,
        [
            "gen",
            str(spec_path),
            "--output",
            str(output_dir),
            "--template",
            str(SAMPLE_TEMPLATE),
            *_brief_args(brief_paths),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "Polisher: disabled" in result.output

    spec = JobSpec.parse_file(spec_path)

    pptx_path = output_dir / "proposal.pptx"
    analysis_path = output_dir / "analysis.json"
    baseline_analysis_path = output_dir / "analysis_pre_polisher.json"
    audit_path = output_dir / "audit_log.json"
    rendering_log_path = output_dir / "rendering_log.json"
    monitoring_report_path = output_dir / "monitoring_report.json"

    assert pptx_path.exists()
    assert analysis_path.exists()
    assert baseline_analysis_path.exists()
    assert audit_path.exists()
    assert rendering_log_path.exists()
    assert monitoring_report_path.exists()

    payload = json.loads(analysis_path.read_text(encoding="utf-8"))
    assert payload.get("slides") == len(spec.slides)
    assert isinstance(payload.get("issues"), list)
    assert isinstance(payload.get("fixes"), list)
    assert payload.get("meta", {}).get("title") == spec.meta.title

    rendering_log = json.loads(rendering_log_path.read_text(encoding="utf-8"))
    assert rendering_log["meta"]["warnings_total"] >= 0

    monitoring_report = json.loads(monitoring_report_path.read_text(encoding="utf-8"))
    assert monitoring_report.get("rendering", {}).get("warnings_total") == rendering_log["meta"]["warnings_total"]
    analyzer_meta = monitoring_report.get("analyzer", {})
    assert "after_pipeline" in analyzer_meta

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit_payload.get("slides") == len(spec.slides)
    assert audit_payload.get("pdf_export") is None
    hashes = audit_payload.get("hashes")
    assert isinstance(hashes, dict)
    assert hashes.get("pptx", "").startswith("sha256:")
    assert hashes.get("analysis", "").startswith("sha256:")
    assert hashes.get("analysis_pre_polisher", "").startswith("sha256:")
    assert hashes.get("rendering_ready", "").startswith("sha256:")
    assert hashes.get("rendering_log", "").startswith("sha256:")
    assert hashes.get("monitoring_report", "").startswith("sha256:")
    assert hashes.get("mapping_log", "").startswith("sha256:")
    rendering_summary = audit_payload.get("rendering")
    assert rendering_summary is not None
    assert rendering_summary.get("warnings_total") == rendering_log["meta"]["warnings_total"]
    monitoring_summary = audit_payload.get("monitoring")
    assert monitoring_summary is not None
    assert monitoring_summary.get("alert_level") in {"ok", "warning", "critical"}
    assert isinstance(audit_payload.get("refiner_adjustments"), list)
    branding_info = audit_payload.get("branding")
    assert branding_info is not None
    assert branding_info.get("source", {}).get("type") == "template"
    assert branding_info.get("source", {}).get("template") == str(SAMPLE_TEMPLATE)
    mapping_info = audit_payload.get("mapping")
    assert mapping_info is not None
    assert mapping_info.get("slides") == len(spec.slides)
    assert mapping_info.get("rendering_ready_path") == str((output_dir / "rendering_ready.json"))
    assert mapping_info.get("fallback_count") == 0
    assert mapping_info.get("ai_patch_count") == 0
    polisher_meta = audit_payload.get("polisher")
    assert polisher_meta is not None
    assert polisher_meta.get("status") == "disabled"
    assert polisher_meta.get("enabled") is False

    presentation = Presentation(pptx_path)
    assert len(presentation.slides) == len(spec.slides)

    for slide_spec, slide in zip(spec.slides, presentation.slides, strict=False):
        if not slide_spec.title:
            continue
        title_shape = slide.shapes.title
        if title_shape is None:
            continue
        actual = title_shape.text
        assert actual == slide_spec.title

    agenda_spec = next(slide for slide in spec.slides if slide.id == "agenda-01")
    agenda_index = spec.slides.index(agenda_spec)
    agenda_slide = presentation.slides[agenda_index]
    images = [shape for shape in agenda_slide.shapes if shape.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert images, "画像が描画されていること"

    table_spec = next(slide for slide in spec.slides if getattr(slide, "tables", None))
    table_slide = presentation.slides[spec.slides.index(table_spec)]
    tables = [shape for shape in table_slide.shapes if getattr(shape, "has_table", False)]
    assert tables, "テーブルが描画されていること"

    chart_spec = next(slide for slide in spec.slides if getattr(slide, "charts", None))
    chart_slide = presentation.slides[spec.slides.index(chart_spec)]
    charts = [shape for shape in chart_slide.shapes if getattr(shape, "has_chart", False)]
    assert charts, "チャートが描画されていること"


def test_cli_content_generates_brief_outputs(tmp_path) -> None:
    output_dir = tmp_path / "brief"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "content",
            str(BRIEF_SOURCE),
            "--output",
            str(output_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    cards_path = output_dir / "brief_cards.json"
    meta_path = output_dir / "ai_generation_meta.json"
    log_path = output_dir / "brief_ai_log.json"
    audit_path = output_dir / "audit_log.json"

    assert cards_path.exists()
    assert meta_path.exists()
    assert log_path.exists()
    assert audit_path.exists()

    cards_payload = json.loads(cards_path.read_text(encoding="utf-8"))
    assert len(cards_payload["cards"]) >= 1
    meta_payload = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta_payload["policy_id"]
    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit_payload["brief_normalization"]["statistics"]["cards_total"] == len(cards_payload["cards"])


def test_cli_gen_with_brief_inputs(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    output_dir = tmp_path / "gen-brief"
    runner = CliRunner()
    spec = JobSpec.parse_file(spec_path)
    brief_paths = _prepare_brief_inputs(runner, tmp_path)

    result = runner.invoke(
        app,
        [
            "gen",
            str(spec_path),
            "--output",
            str(output_dir),
            "--template",
            str(SAMPLE_TEMPLATE),
            *_brief_args(brief_paths),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output

    audit_path = output_dir / "audit_log.json"
    assert audit_path.exists()
    baseline_analysis_path = output_dir / "analysis_pre_polisher.json"
    assert baseline_analysis_path.exists()
    monitoring_report_path = output_dir / "monitoring_report.json"
    assert monitoring_report_path.exists()

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    rendering_summary = audit_payload.get("rendering")
    assert rendering_summary is not None
    assert rendering_summary.get("warnings_total") >= 0
    hashes = audit_payload.get("hashes")
    assert isinstance(hashes, dict)
    assert hashes.get("pptx", "").startswith("sha256:")
    assert hashes.get("rendering_ready", "").startswith("sha256:")
    assert hashes.get("analysis_pre_polisher", "").startswith("sha256:")
    assert hashes.get("rendering_log", "").startswith("sha256:")
    assert hashes.get("monitoring_report", "").startswith("sha256:")
    assert hashes.get("mapping_log", "").startswith("sha256:")
    assert isinstance(audit_payload.get("refiner_adjustments"), list)
    monitoring_summary = audit_payload.get("monitoring")
    assert monitoring_summary is not None
    assert "alert_level" in monitoring_summary
    mapping_info = audit_payload.get("mapping")
    assert mapping_info is not None
    assert mapping_info.get("rendering_ready_path") == str((output_dir / "rendering_ready.json"))
    assert mapping_info.get("fallback_count") >= 0
    polisher_meta = audit_payload.get("polisher")
    assert polisher_meta is not None
    assert polisher_meta.get("status") == "disabled"
    assert polisher_meta.get("enabled") is False

    presentation = Presentation(output_dir / "proposal.pptx")

    agenda_spec = next(slide for slide in spec.slides if slide.id == "agenda-01")
    agenda_slide = presentation.slides[spec.slides.index(agenda_spec)]
    agenda_texts = _collect_paragraph_texts(agenda_slide)
    assert agenda_spec.subtitle in agenda_texts
    assert "Agenda トピック 1-1" in agenda_texts
    assert "Agenda トピック 1-2" in agenda_texts

    detail_spec = next(slide for slide in spec.slides if slide.id == "three_rows_detail-01")
    detail_slide = presentation.slides[spec.slides.index(detail_spec)]
    assert detail_slide.notes_slide is not None


def test_cli_mapping_then_render(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    mapping_dir = tmp_path / "mapping"
    render_dir = tmp_path / "render"
    draft_dir = tmp_path / "draft"

    runner = CliRunner()
    brief_paths = _prepare_brief_inputs(runner, tmp_path)

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
            *_brief_args(brief_paths),
        ],
        catch_exceptions=False,
    )

    assert mapping_result.exit_code == 0

    rendering_ready_path = mapping_dir / "rendering_ready.json"
    mapping_log_path = mapping_dir / "mapping_log.json"
    assert rendering_ready_path.exists()
    assert mapping_log_path.exists()

    render_result = runner.invoke(
        app,
        [
            "render",
            str(rendering_ready_path),
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
    assert hashes.get("rendering_ready", "").startswith("sha256:")
    # mapping_log は別ディレクトリのため単体 render 実行ではハッシュ対象外
    assert hashes.get("mapping_log") is None
    artifacts = audit_payload.get("artifacts", {})
    assert artifacts.get("rendering_ready") == str(rendering_ready_path)


def test_cli_compose_generates_stage45_outputs(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    draft_dir = tmp_path / "compose-draft"
    output_dir = tmp_path / "compose-gen"
    runner = CliRunner()
    brief_paths = _prepare_brief_inputs(runner, tmp_path)

    result = runner.invoke(
        app,
        [
            "compose",
            str(spec_path),
            "--draft-output",
            str(draft_dir),
            "--output",
            str(output_dir),
            "--template",
            str(SAMPLE_TEMPLATE),
            *_brief_args(brief_paths),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert "Outline Draft:" in result.output
    assert "Rendering Ready:" in result.output

    spec = JobSpec.parse_file(spec_path)

    draft_meta_path = draft_dir / "draft_meta.json"
    assert (draft_dir / "draft_draft.json").exists()
    assert (draft_dir / "draft_approved.json").exists()
    assert (draft_dir / "draft_review_log.json").exists()
    assert draft_meta_path.exists()

    draft_meta = json.loads(draft_meta_path.read_text(encoding="utf-8"))
    paths = draft_meta.get("paths", {})
    assert Path(paths.get("draft_approved", "")).exists()
    assert Path(paths.get("draft_review_log", "")).exists()

    rendering_ready_path = output_dir / "rendering_ready.json"
    mapping_log_path = output_dir / "mapping_log.json"
    assert rendering_ready_path.exists()
    assert mapping_log_path.exists()

    rendering_ready = json.loads(rendering_ready_path.read_text(encoding="utf-8"))
    assert len(rendering_ready.get("slides", [])) == len(spec.slides)

    mapping_log = json.loads(mapping_log_path.read_text(encoding="utf-8"))
    assert mapping_log.get("slides")


def test_cli_gen_with_invalid_brief_fails(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    invalid_brief = tmp_path / "invalid_brief.json"
    invalid_brief.write_text(
        json.dumps(
            {
                "brief_id": "invalid",
                "cards": [
                    {
                        "card_id": "s01",
                        "chapter": "Overview",
                        "message": "Missing story",
                        "narrative": [],
                        "supporting_points": [],
                        "intent_tags": [],
                        "status": "draft",
                        "autofix_applied": [],
                    }
                ],
                "story_context": {"chapters": []},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    brief_log = tmp_path / "brief_log.json"
    brief_log.write_text("[]", encoding="utf-8")
    brief_meta = tmp_path / "ai_generation_meta.json"
    brief_meta.write_text(
        json.dumps(
            {
                "brief_id": "invalid",
                "generated_at": "2025-11-02T00:00:00Z",
                "policy_id": "brief-default",
                "input_hash": "sha256:d41d8cd98f00b204e9800998ecf8427e",
                "cards": [],
                "statistics": {"cards_total": 1, "approved": 0, "returned": 0},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    output_dir = tmp_path / "gen-invalid-brief"
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
            "--brief-cards",
            str(invalid_brief),
            "--brief-log",
            str(brief_log),
            "--brief-meta",
            str(brief_meta),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 4
    assert "ブリーフ成果物の読み込みに失敗しました" in result.output
    assert not (output_dir / "audit_log.json").exists()


def test_cli_gen_missing_brief_files_fail(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    output_dir = tmp_path / "gen-missing-brief"
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
            "--brief-cards",
            str(tmp_path / "missing_brief.json"),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 4
    assert "ブリーフ成果物の読み込みに失敗しました" in result.output
    assert not (output_dir / "audit_log.json").exists()


def test_cli_gen_supports_template(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    output_dir = tmp_path / "gen-work-template"
    template_path = tmp_path / "template.pptx"

    shutil.copyfile(SAMPLE_TEMPLATE, template_path)

    spec = JobSpec.parse_file(spec_path)

    runner = CliRunner()
    brief_paths = _prepare_brief_inputs(runner, tmp_path)
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
            *_brief_args(brief_paths),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    pptx_path = output_dir / "with-template.pptx"
    analysis_path = output_dir / "analysis.json"
    review_engine_path = output_dir / "review_engine_analyzer.json"
    audit_path = output_dir / "audit_log.json"
    assert pptx_path.exists()
    assert analysis_path.exists()
    assert review_engine_path.exists()
    assert audit_path.exists()

    presentation = Presentation(pptx_path)
    assert len(presentation.slides) == len(spec.slides)

    audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert isinstance(audit_payload.get("refiner_adjustments"), list)
    branding_info = audit_payload.get("branding")
    assert branding_info is not None
    assert branding_info.get("source", {}).get("type") == "template"
    assert "config" in branding_info

    review_payload = json.loads(review_engine_path.read_text(encoding="utf-8"))
    assert review_payload.get("slides")
    assert review_payload["slides"][0]["issues"]

    for slide_spec, slide in zip(spec.slides, presentation.slides, strict=False):
        if not slide_spec.title:
            continue
        title_shape = slide.shapes.title
        if title_shape is None:
            continue
        actual = title_shape.text
        assert actual == slide_spec.title


def test_cli_gen_with_polisher_stub(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    output_dir = tmp_path / "gen-polisher"
    rules_path = tmp_path / "polisher-rules.json"
    rules_path.write_text(json.dumps({"min_font_size_pt": 18.0}), encoding="utf-8")

    script_path = tmp_path / "polisher_stub.py"
    script_path.write_text(
        "\n".join(
            [
                "import argparse",
                "import json",
                "from pathlib import Path",
                "",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--input', required=True)",
                "parser.add_argument('--rules', required=True)",
                "args = parser.parse_args()",
                "path = Path(args.input)",
                "path.read_bytes()",  # ensureファイル存在
                "Path(args.rules).touch(exist_ok=True)",
                "print(json.dumps({'stub': 'ok', 'adjusted_font_size': 0}))",
            ]
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    brief_paths = _prepare_brief_inputs(runner, tmp_path)
    result = runner.invoke(
        app,
        [
            "gen",
            str(spec_path),
            "--output",
            str(output_dir),
            "--template",
            str(SAMPLE_TEMPLATE),
            *_brief_args(brief_paths),
            "--polisher",
            "--polisher-path",
            sys.executable,
            "--polisher-arg",
            str(script_path),
            "--polisher-arg",
            "--input",
            "--polisher-arg",
            "{pptx}",
            "--polisher-arg",
            "--rules",
            "--polisher-arg",
            "{rules}",
            "--polisher-rules",
            str(rules_path),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "Polisher: success" in result.output

    audit_payload = json.loads((output_dir / "audit_log.json").read_text(encoding="utf-8"))
    polisher_meta = audit_payload.get("polisher")
    assert polisher_meta is not None
    assert polisher_meta.get("status") == "success"
    assert polisher_meta.get("enabled") is True
    assert polisher_meta.get("elapsed_ms") >= 0
    assert polisher_meta.get("rules_path") == str(rules_path)
    summary = polisher_meta.get("summary")
    assert isinstance(summary, dict)
    assert summary.get("stub") == "ok"


def test_cli_gen_template_with_explicit_branding(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
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
    brief_paths = _prepare_brief_inputs(runner, tmp_path)
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
            *_brief_args(brief_paths),
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
    spec_path = Path("samples/json/sample_jobspec.json")
    template_path = Path("samples/templates/templates.pptx")
    output_dir = tmp_path / "gen-work-template-fallback"

    def raise_error(_: Path) -> None:
        raise BrandingExtractionError("boom")

    monkeypatch.setattr("pptx_generator.cli.extract_branding_config", raise_error)

    runner = CliRunner()
    brief_paths = _prepare_brief_inputs(runner, tmp_path)
    result = runner.invoke(
        app,
        [
            "gen",
            str(spec_path),
            "--output",
            str(output_dir),
            "--template",
            str(template_path),
            *_brief_args(brief_paths),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    audit_payload = json.loads((output_dir / "audit_log.json").read_text(encoding="utf-8"))
    branding_info = audit_payload.get("branding")
    assert branding_info is not None
    assert branding_info.get("source", {}).get("type") in {"default", "builtin"}
    assert branding_info.get("source", {}).get("error") == "boom"


def test_cli_mapping_command_generates_outputs(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    output_dir = tmp_path / "mapping-work"
    runner = CliRunner()
    brief_paths = _prepare_brief_inputs(runner, tmp_path)

    result = runner.invoke(
        app,
        [
            "mapping",
            str(spec_path),
            "--output",
            str(output_dir),
            *_brief_args(brief_paths),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    rendering_ready_path = output_dir / "rendering_ready.json"
    mapping_log_path = output_dir / "mapping_log.json"
    assert rendering_ready_path.exists()
    assert mapping_log_path.exists()

    payload = json.loads(rendering_ready_path.read_text(encoding="utf-8"))
    assert payload["meta"]["job_meta"]["title"] == "RM-043 拡張テンプレート検証"
    assert payload["meta"]["job_auth"]["created_by"] == "codex"


def test_cli_render_command_consumes_rendering_ready(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    mapping_dir = tmp_path / "mapping-work"
    render_dir = tmp_path / "render-work"
    runner = CliRunner()
    brief_paths = _prepare_brief_inputs(runner, tmp_path)

    mapping_result = runner.invoke(
        app,
        [
            "mapping",
            str(spec_path),
            "--output",
            str(mapping_dir),
            "--template",
            str(SAMPLE_TEMPLATE),
            *_brief_args(brief_paths),
        ],
        catch_exceptions=False,
    )
    assert mapping_result.exit_code == 0

    rendering_ready_path = mapping_dir / "rendering_ready.json"
    assert rendering_ready_path.exists()

    render_result = runner.invoke(
        app,
        [
            "render",
            str(rendering_ready_path),
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
    assert audit_payload["artifacts"]["rendering_ready"] == str(rendering_ready_path)
    assert audit_payload["artifacts"]["rendering_log"].endswith("rendering_log.json")
    rendering_summary = audit_payload.get("rendering")
    assert rendering_summary is not None
    assert rendering_summary.get("warnings_total") >= 0
    spec = JobSpec.parse_file(spec_path)
    assert audit_payload["slides"] == len(spec.slides)


def test_cli_layout_validate_with_analyzer_snapshot(tmp_path) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    template_path = SAMPLE_TEMPLATE
    gen_output = tmp_path / "gen-with-snapshot"
    validation_output = tmp_path / "validation-with-snapshot"

    runner = CliRunner()
    brief_paths = _prepare_brief_inputs(runner, tmp_path)
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
            *_brief_args(brief_paths),
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
    spec_path = Path("samples/json/sample_jobspec.json")
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
    brief_paths = _prepare_brief_inputs(runner, tmp_path)
    result = runner.invoke(
        app,
        [
            "gen",
            str(spec_path),
            "--output",
            str(output_dir),
            "--template",
            str(SAMPLE_TEMPLATE),
            *_brief_args(brief_paths),
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
    assert pdf_meta.get("status") == "success"
    assert pdf_meta.get("elapsed_ms") >= 0
    assert isinstance(audit_payload.get("refiner_adjustments"), list)


def test_cli_gen_pdf_only(tmp_path, monkeypatch) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
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
    brief_paths = _prepare_brief_inputs(runner, tmp_path)
    result = runner.invoke(
        app,
        [
            "gen",
            str(spec_path),
            "--output",
            str(output_dir),
            "--template",
            str(SAMPLE_TEMPLATE),
            *_brief_args(brief_paths),
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
    pdf_meta = audit_payload.get("pdf_export")
    assert pdf_meta is not None
    assert pdf_meta.get("status") == "success"
    assert pdf_meta.get("converter") == "libreoffice"


def test_cli_gen_pdf_skip_env(tmp_path, monkeypatch) -> None:
    spec_path = Path("samples/json/sample_jobspec.json")
    output_dir = tmp_path / "gen-work-pdf-skip"

    def fail_run(*args, **kwargs):  # noqa: ANN401
        raise AssertionError("LibreOffice should not be invoked when skip env is set")

    monkeypatch.setenv("PPTXGEN_SKIP_PDF_CONVERT", "1")
    monkeypatch.setattr(pdf_exporter.subprocess, "run", fail_run)

    runner = CliRunner()
    brief_paths = _prepare_brief_inputs(runner, tmp_path)
    result = runner.invoke(
        app,
        [
            "gen",
            str(spec_path),
            "--output",
            str(output_dir),
            "--template",
            str(SAMPLE_TEMPLATE),
            *_brief_args(brief_paths),
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
    pdf_meta = audit_payload.get("pdf_export")
    assert pdf_meta is not None
    assert pdf_meta.get("converter") == "skipped"
    assert pdf_meta.get("status") == "skipped"


def test_cli_gen_default_output_directory(tmp_path) -> None:
    runner = CliRunner()
    repo_root = Path(__file__).resolve().parents[1]

    with runner.isolated_filesystem(temp_dir=tmp_path) as fs:
        fs_root = Path(fs)
        shutil.copytree(repo_root / "samples", fs_root / "samples")
        shutil.copytree(repo_root / "config", fs_root / "config")

        brief_paths = _prepare_brief_inputs(runner, fs_root)
        result = runner.invoke(
            app,
            [
                "gen",
                "samples/json/sample_jobspec.json",
                "--template",
                "samples/templates/templates.pptx",
                *_brief_args(brief_paths),
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


def test_cli_tpl_extract_validation_failure_exits_with_error(tmp_path, monkeypatch) -> None:
    runner = CliRunner()
    repo_root = Path(__file__).resolve().parents[1]

    with runner.isolated_filesystem(temp_dir=tmp_path) as fs:
        fs_root = Path(fs)
        shutil.copytree(repo_root / "samples", fs_root / "samples")

        output_dir = Path("out-validation")
        validation_result = LayoutValidationResult(
            layouts_path=output_dir / "layouts.jsonl",
            diagnostics_path=output_dir / "diagnostics.json",
            diff_report_path=None,
            record_count=0,
            warnings_count=0,
            errors_count=2,
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        validation_result.layouts_path.write_text("[]", encoding="utf-8")
        validation_result.diagnostics_path.write_text("{}", encoding="utf-8")

        monkeypatch.setattr(LayoutValidationSuite, "run", lambda self: validation_result)

        result = runner.invoke(
            app,
            [
                "tpl-extract",
                "--template",
                "samples/templates/templates.pptx",
                "--output",
                str(output_dir),
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 6
        assert "レイアウト検証でエラーが検出されました" in result.output


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
