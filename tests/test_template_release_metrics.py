"""テンプレートリリースにおける Analyzer メトリクス集計のテスト。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pptx_generator.models import (
    LayoutInfo,
    ShapeInfo,
    TemplateRelease,
    TemplateReleaseEnvironment,
    TemplateReleaseGoldenRun,
    TemplateSpec,
)
from pptx_generator.template_audit.release import (
    build_release_report,
    build_template_release,
)
from pptx_generator.template_audit import release as release_module


@pytest.fixture(autouse=True)
def fixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    environment = TemplateReleaseEnvironment(
        python_version="3.12.1",
        platform="TestOS",
        pptx_generator_version="0.1.0",
        libreoffice_version="LibreOffice 7.6.0",
        dotnet_sdk_version="8.0.0",
    )
    monkeypatch.setattr(
        release_module,
        "collect_environment_info",
        lambda: (environment, []),
    )


def _write_template(path: Path) -> None:
    path.write_bytes(b"dummy pptx payload")


def _write_analysis(path: Path, issues: list[dict], fixes: list[dict]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "issues": issues,
        "fixes": fixes,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_spec(template_path: Path) -> TemplateSpec:
    return TemplateSpec(
        template_path=str(template_path),
        extracted_at=datetime.now(timezone.utc).isoformat(),
        layouts=[
            LayoutInfo(
                name="title",
                anchors=[
                    ShapeInfo(
                        name="PH__Title",
                        shape_type="text",
                        left_in=0.0,
                        top_in=0.0,
                        width_in=1.0,
                        height_in=1.0,
                        is_placeholder=True,
                    )
                ],
            )
        ],
    )


def _make_golden_run(spec_path: str, analysis_path: Path) -> TemplateReleaseGoldenRun:
    return TemplateReleaseGoldenRun(
        spec_path=spec_path,
        status="passed",
        output_dir=str(Path(analysis_path).parent),
        pptx_path=None,
        analysis_path=str(analysis_path),
        pdf_path=None,
        warnings=[],
        errors=[],
    )


def test_build_template_release_collects_analyzer_metrics(tmp_path) -> None:
    template_path = tmp_path / "template.pptx"
    _write_template(template_path)
    spec = _make_spec(template_path)

    analysis_path = tmp_path / "analysis.json"
    _write_analysis(
        analysis_path,
        issues=[
            {"type": "font_min", "severity": "warning"},
            {"type": "contrast_low", "severity": "error"},
        ],
        fixes=[
            {"type": "font_raise"},
            {"type": "color_adjust"},
        ],
    )

    release = build_template_release(
        template_path=template_path,
        spec=spec,
        template_id="sample_v1",
        brand="Sample",
        version="1.0.0",
        golden_runs=[_make_golden_run("spec.json", analysis_path)],
    )

    metrics = release.analyzer_metrics
    assert metrics is not None
    assert metrics.summary.run_count == 1
    assert metrics.summary.issues.total == 2
    assert metrics.summary.issues.by_type["font_min"] == 1
    assert metrics.summary.issues.by_type["contrast_low"] == 1
    assert metrics.summary.issues.by_severity["warning"] == 1
    assert metrics.summary.issues.by_severity["error"] == 1
    assert metrics.summary.fixes.total == 2
    assert metrics.summary.fixes.by_type["font_raise"] == 1
    assert metrics.summary.fixes.by_type["color_adjust"] == 1
    assert metrics.runs[0].status == "included"
    assert release.summary.analyzer_issue_total == 2
    assert release.summary.analyzer_fix_total == 2
    assert release.environment.pptx_generator_version == "0.1.0"


def test_build_release_report_includes_analyzer_delta(tmp_path) -> None:
    template_path = tmp_path / "template.pptx"
    _write_template(template_path)
    spec = _make_spec(template_path)

    analysis_base = tmp_path / "analysis_base.json"
    _write_analysis(
        analysis_base,
        issues=[{"type": "font_min", "severity": "warning"}],
        fixes=[{"type": "font_raise"}],
    )
    baseline = build_template_release(
        template_path=template_path,
        spec=spec,
        template_id="sample_v1",
        brand="Sample",
        version="1.0.0",
        golden_runs=[_make_golden_run("spec.json", analysis_base)],
    )

    analysis_current = tmp_path / "analysis_current.json"
    _write_analysis(
        analysis_current,
        issues=[
            {"type": "font_min", "severity": "warning"},
            {"type": "contrast_low", "severity": "error"},
        ],
        fixes=[
            {"type": "font_raise"},
            {"type": "color_adjust"},
        ],
    )
    current = build_template_release(
        template_path=template_path,
        spec=spec,
        template_id="sample_v2",
        brand="Sample",
        version="1.1.0",
        golden_runs=[_make_golden_run("spec.json", analysis_current)],
    )

    report = build_release_report(current=current, baseline=baseline)
    assert report.analyzer is not None
    assert report.analyzer.current.issues.total == 2
    assert report.analyzer.baseline is not None
    assert report.analyzer.baseline.issues.total == 1
    assert report.analyzer.delta is not None
    assert report.analyzer.delta.total_issue_change == 1
    assert report.analyzer.delta.total_fix_change == 1
    assert report.analyzer.delta.issues["contrast_low"] == 1
    assert report.analyzer.delta.issues["font_min"] == 0
    assert report.analyzer.delta.severity["error"] == 1
    assert report.analyzer.delta.severity["warning"] == 0
    assert report.summary.analyzer_issue_total == 2
    assert report.summary_baseline is not None
    assert report.summary_baseline.analyzer_issue_total == 1
    assert report.summary_delta is not None
    assert report.summary_delta.analyzer_issue_total == 1
