"""テンプレートリリース生成ロジックのテスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

from pptx_generator.models import (LayoutInfo, ShapeInfo, TemplateReleaseGoldenRun,
                                   TemplateSpec)
from pptx_generator.template_audit import build_release_report, build_template_release


def _create_template_file(tmp_path: Path, name: str, content: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    return path


def test_build_template_release_collects_warnings(tmp_path: Path) -> None:
    template_path = _create_template_file(tmp_path, "template.pptx", b"dummy-content")

    duplicate_shape = ShapeInfo(
        name="PH__Title",
        shape_type="Shape",
        left_in=0.0,
        top_in=0.0,
        width_in=5.0,
        height_in=2.0,
        text=None,
        placeholder_type="TITLE",
        is_placeholder=True,
    )
    missing_shape = ShapeInfo(
        name="Body",
        shape_type="Shape",
        left_in=1.0,
        top_in=1.0,
        width_in=0.0,
        height_in=2.0,
        text=None,
        placeholder_type=None,
        is_placeholder=False,
        missing_fields=["width"],
        conflict="SlideBullet拡張仕様で使用される可能性のあるアンカー名: body",
    )

    spec = TemplateSpec(
        template_path=str(template_path),
        extracted_at="2025-10-12T00:00:00+00:00",
        layouts=[
            LayoutInfo(
                name="title_layout",
                anchors=[duplicate_shape, duplicate_shape, missing_shape],
            )
        ],
        warnings=["shape count mismatch"],
        errors=[],
    )

    release = build_template_release(
        template_path=template_path,
        spec=spec,
        template_id="Sample_v1",
        brand="Sample",
        version="1.0.0",
        generated_by="tester",
        reviewed_by=None,
    )

    assert release.layouts.total == 1
    assert pytest.approx(release.layouts.placeholders_avg, rel=1e-5) == 2.0
    detail = release.layouts.details[0]
    assert detail.duplicate_anchor_names == ["PH__Title"]
    assert any("missing_fields: width" in issue for issue in detail.issues)
    assert any("conflict" in issue for issue in detail.issues)
    assert release.extractor == {
        "extracted_at": spec.extracted_at,
        "source_template": spec.template_path,
    }
    warnings = release.diagnostics.warnings
    assert any("duplicate anchors" in message for message in warnings)
    assert any("missing fields" in message for message in warnings)
    assert any(
        "SlideBullet拡張仕様で使用される可能性のあるアンカー名" in message
        for message in warnings
    )
    assert any("extractor: shape count mismatch" == message for message in warnings)
    assert release.golden_runs == []


def test_build_release_report_detects_anchor_changes(tmp_path: Path) -> None:
    baseline_path = _create_template_file(tmp_path, "baseline.pptx", b"baseline")
    current_path = _create_template_file(tmp_path, "current.pptx", b"current")

    baseline_spec = TemplateSpec(
        template_path=str(baseline_path),
        extracted_at="2025-10-12T00:00:00+00:00",
        layouts=[
            LayoutInfo(
                name="title_layout",
                anchors=[
                    ShapeInfo(
                        name="PH__Title",
                        shape_type="Shape",
                        left_in=0.0,
                        top_in=0.0,
                        width_in=5.0,
                        height_in=2.0,
                        text=None,
                        placeholder_type="TITLE",
                        is_placeholder=True,
                    )
                ],
            )
        ],
        warnings=[],
        errors=[],
    )

    current_spec = TemplateSpec(
        template_path=str(current_path),
        extracted_at="2025-10-12T00:10:00+00:00",
        layouts=[
            LayoutInfo(
                name="title_layout",
                anchors=[
                    ShapeInfo(
                        name="PH__Title",
                        shape_type="Shape",
                        left_in=0.0,
                        top_in=0.0,
                        width_in=5.0,
                        height_in=2.0,
                        text=None,
                        placeholder_type="TITLE",
                        is_placeholder=True,
                    ),
                    ShapeInfo(
                        name="PH__Subtitle",
                        shape_type="Shape",
                        left_in=1.0,
                        top_in=1.0,
                        width_in=4.0,
                        height_in=1.5,
                        text=None,
                        placeholder_type="SUBTITLE",
                        is_placeholder=True,
                    ),
                ],
            )
        ],
        warnings=[],
        errors=[],
    )

    baseline_release = build_template_release(
        template_path=baseline_path,
        spec=baseline_spec,
        template_id="Sample_v1",
        brand="Sample",
        version="1.0.0",
    )
    current_release = build_template_release(
        template_path=current_path,
        spec=current_spec,
        template_id="Sample_v2",
        brand="Sample",
        version="1.1.0",
    )

    report = build_release_report(current=current_release, baseline=baseline_release)
    assert report.changes.layouts_added == []
    assert report.changes.layouts_removed == []
    assert report.changes.layout_diffs
    diff = report.changes.layout_diffs[0]
    assert diff.name == "title_layout"
    assert diff.anchors_added == ["PH__Subtitle"]
    assert diff.placeholders_added == ["PH__Subtitle"]


def test_build_template_release_with_golden_runs(tmp_path: Path) -> None:
    template_path = _create_template_file(tmp_path, "template.pptx", b"dummy")

    spec = TemplateSpec(
        template_path=str(template_path),
        extracted_at="2025-10-12T00:00:00+00:00",
        layouts=[],
        warnings=[],
        errors=[],
    )

    golden = TemplateReleaseGoldenRun(
        spec_path="samples/json/sample_spec.json",
        status="failed",
        output_dir=".pptx/release/golden_runs/sample_spec",
        pptx_path=None,
        analysis_path=None,
        pdf_path=None,
        warnings=["analyzer warning"],
        errors=["render error"],
    )

    release = build_template_release(
        template_path=template_path,
        spec=spec,
        template_id="Sample_v1",
        brand="Sample",
        version="1.0.0",
        golden_runs=[golden],
        extra_warnings=["golden warning"],
        extra_errors=["golden error"],
    )

    assert len(release.golden_runs) == 1
    stored = release.golden_runs[0]
    assert stored.status == "failed"
    assert "golden warning" in release.diagnostics.warnings
    assert "golden error" in release.diagnostics.errors
