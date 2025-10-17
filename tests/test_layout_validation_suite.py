from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from pptx_generator.cli import app
from pptx_generator.layout_validation import (
    LayoutValidationOptions,
    LayoutValidationSuite,
)
from pptx_generator.models import LayoutInfo, TemplateSpec
from pptx_generator.pipeline.template_extractor import (
    TemplateExtractor,
    TemplateExtractorOptions,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT_DIR / "samples" / "templates" / "templates.pptx"


def test_layout_validation_suite_creates_outputs(tmp_path) -> None:
    options = LayoutValidationOptions(
        template_path=TEMPLATE_PATH,
        output_dir=tmp_path,
        template_id="sample",
    )
    suite = LayoutValidationSuite(options)

    result = suite.run()

    assert result.layouts_path.exists()
    assert result.diagnostics_path.exists()
    assert result.record_count > 0

    layouts_lines = result.layouts_path.read_text(encoding="utf-8").strip().splitlines()
    assert layouts_lines, "layouts.jsonl が空です"
    first_record = json.loads(layouts_lines[0])
    assert first_record["template_id"] == "sample"
    assert "placeholders" in first_record

    diagnostics = json.loads(result.diagnostics_path.read_text(encoding="utf-8"))
    assert diagnostics["stats"]["layouts_total"] >= result.record_count


def test_layout_validation_suite_generates_diff_report(tmp_path) -> None:
    output_dir = tmp_path / "current"
    options = LayoutValidationOptions(
        template_path=TEMPLATE_PATH,
        output_dir=output_dir,
        template_id="sample",
    )
    suite = LayoutValidationSuite(options)
    first_run = suite.run()

    baseline_path = tmp_path / "baseline.jsonl"
    records = []
    for line in first_run.layouts_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))

    # bbox を 1 つだけ変更して差分検出を確認する
    records[0]["placeholders"][0]["bbox"]["width"] += 1000

    with baseline_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False))
            file.write("\n")

    options_with_baseline = LayoutValidationOptions(
        template_path=TEMPLATE_PATH,
        output_dir=tmp_path / "with_baseline",
        template_id="sample",
        baseline_path=baseline_path,
    )
    suite_with_baseline = LayoutValidationSuite(options_with_baseline)
    result = suite_with_baseline.run()

    assert result.diff_report_path is not None
    diff_report = json.loads(result.diff_report_path.read_text(encoding="utf-8"))
    assert diff_report["placeholders_changed"], "差分が検出されていません"


def test_cli_layout_validate_command(tmp_path) -> None:
    output_dir = tmp_path / "cli"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "layout-validate",
            "--template",
            str(TEMPLATE_PATH),
            "--output",
            str(output_dir),
            "--template-id",
            "sample",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (output_dir / "layouts.jsonl").exists()
    assert (output_dir / "diagnostics.json").exists()


def test_layout_diff_uses_stable_ids_for_duplicate_names(tmp_path) -> None:
    layout_a = LayoutInfo(name="Title", identifier="1001", anchors=[])
    layout_b = LayoutInfo(name="Title", identifier="1002", anchors=[])
    spec = TemplateSpec(
        template_path="dummy",
        extracted_at="2024-10-15T00:00:00Z",
        layouts=[layout_a, layout_b],
        warnings=[],
        errors=[],
    )
    options = LayoutValidationOptions(
        template_path=tmp_path / "template.pptx",
        output_dir=tmp_path,
        template_id="sample",
    )
    suite = LayoutValidationSuite(options)

    records, _, _ = suite._build_layout_records(spec, "sample")

    baseline_path = tmp_path / "baseline.jsonl"
    with baseline_path.open("w", encoding="utf-8") as file:
        for record in reversed(records):
            file.write(json.dumps(record, ensure_ascii=False))
            file.write("\n")

    diff_report = suite._build_diff_report(
        records=records,
        target_template_id="sample",
        baseline_path=baseline_path,
    )

    assert diff_report is not None
    assert diff_report["layouts_added"] == []
    assert diff_report["layouts_removed"] == []
    assert diff_report["placeholders_changed"] == []


def test_layout_validation_reports_analyzer_snapshot_gaps(tmp_path) -> None:
    extractor = TemplateExtractor(
        TemplateExtractorOptions(template_path=TEMPLATE_PATH)
    )
    template_spec = extractor.extract()
    layout = template_spec.layouts[0]
    anchor_name = next(
        (anchor.name for anchor in layout.anchors if anchor.name), None
    )
    assert anchor_name is not None, "テンプレートに名前付きアンカーが必要です"

    snapshot_payload = {
        "schema_version": "1.0.0",
        "slides": [
            {
                "index": 0,
                "slide_id": "mock-slide",
                "layout": layout.name,
                "placeholders": [
                    {
                        "shape_id": 1,
                        "name": "",
                        "placeholder_type": "BODY",
                        "is_placeholder": True,
                    }
                ],
                "named_shapes": [
                    {
                        "shape_id": 2,
                        "name": "unexpected_anchor",
                    }
                ],
            }
        ],
    }

    snapshot_path = tmp_path / "analysis_snapshot.json"
    snapshot_path.write_text(
        json.dumps(snapshot_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    options = LayoutValidationOptions(
        template_path=TEMPLATE_PATH,
        output_dir=tmp_path / "suite",
        template_id="sample",
        analyzer_snapshot_path=snapshot_path,
    )
    suite = LayoutValidationSuite(options)
    result = suite.run()

    diagnostics = json.loads(result.diagnostics_path.read_text(encoding="utf-8"))
    warning_codes = {(entry["code"], entry.get("name", "")) for entry in diagnostics["warnings"]}

    assert ("analyzer_anchor_missing", anchor_name) in warning_codes
    assert ("analyzer_anchor_unexpected", "unexpected_anchor") in warning_codes

    unnamed_entries = [
        entry for entry in diagnostics["warnings"] if entry["code"] == "analyzer_placeholder_unnamed"
    ]
    assert unnamed_entries, "無名プレースホルダー警告が必要です"

    assert result.diff_report_path is not None
    diff_report = json.loads(result.diff_report_path.read_text(encoding="utf-8"))
    diff_codes = {issue["code"] for issue in diff_report["issues"]}
    assert "analyzer_anchor_missing" in diff_codes
