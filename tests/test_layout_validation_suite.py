from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from pptx_generator.cli import app
from pptx_generator.layout_validation import (
    LayoutValidationOptions,
    LayoutValidationSuite,
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
