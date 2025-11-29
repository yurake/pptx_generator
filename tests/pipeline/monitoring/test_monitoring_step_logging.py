"""MonitoringIntegrationStep の挙動を検証するテスト。"""

from __future__ import annotations

import json
from pathlib import Path

from pptx_generator.models import JobSpec
from pptx_generator.pipeline.base import PipelineContext
from pptx_generator.pipeline.monitoring import MonitoringIntegrationStep


def _build_spec() -> JobSpec:
    payload = {
        "meta": {
            "schema_version": "1.0",
            "title": "監視テスト",
            "locale": "ja-JP",
        },
        "auth": {"created_by": "tester"},
        "slides": [
            {
                "id": "slide-1",
                "layout": "layout_basic",
                "title": "概要",
                "bullets": [{"items": [{"id": "b1", "text": "本文", "level": 0}]}],
                "images": [],
                "textboxes": [],
            }
        ],
    }
    return JobSpec.model_validate(payload)


def test_monitoring_cleanup_runs_when_rendering_log_missing(tmp_path: Path) -> None:
    spec = _build_spec()
    context = PipelineContext(spec=spec, workdir=tmp_path)

    pptx_path = tmp_path / "pdf_only.pptx"
    pptx_path.write_bytes(b"dummy")

    context.add_artifact("pdf_cleanup_pptx_path", str(pptx_path))
    context.add_artifact("pptx_path", str(pptx_path))

    step = MonitoringIntegrationStep()
    step.run(context)

    assert not pptx_path.exists()
    assert "pdf_cleanup_pptx_path" not in context.artifacts
    assert "pptx_path" not in context.artifacts


def test_monitoring_cleanup_runs_after_successful_report(tmp_path: Path) -> None:
    spec = _build_spec()
    context = PipelineContext(spec=spec, workdir=tmp_path)

    pptx_path = tmp_path / "rendered.pptx"
    pptx_path.write_bytes(b"dummy")
    context.add_artifact("pdf_cleanup_pptx_path", str(pptx_path))
    context.add_artifact("pptx_path", str(pptx_path))

    context.add_artifact(
        "rendering_log",
        {
            "meta": {"warnings_total": 0, "empty_placeholders": 0},
            "slides": [{"page_no": 1, "warnings": []}],
        },
    )

    analysis_path = tmp_path / "analysis.json"
    analysis_payload = {
        "slides": 1,
        "meta": spec.meta.model_dump(),
        "issues": [],
        "fixes": [],
    }
    analysis_path.write_text(json.dumps(analysis_payload, ensure_ascii=False), encoding="utf-8")
    context.add_artifact("analysis_path", str(analysis_path))

    step = MonitoringIntegrationStep()
    step.run(context)

    report_path = tmp_path / "monitoring_report.json"
    assert report_path.exists()
    assert context.artifacts.get("monitoring_report_path") == report_path
    assert "monitoring_summary" in context.artifacts
    assert not pptx_path.exists()
    assert "pdf_cleanup_pptx_path" not in context.artifacts
    assert "pptx_path" not in context.artifacts
