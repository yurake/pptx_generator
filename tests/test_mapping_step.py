"""マッピングステップのユニットテスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pptx_generator.models import JobSpec
from pptx_generator.pipeline.base import PipelineContext
from pptx_generator.pipeline.mapping import MappingOptions, MappingStep


def _build_spec(body_lines: Iterable[str]) -> JobSpec:
    """テスト用の最小 JobSpec を構築する。"""
    payload = {
        "meta": {
            "schema_version": "1.0",
            "title": "テスト資料",
            "locale": "ja-JP",
        },
        "auth": {"created_by": "tester"},
        "slides": [
            {
                "id": "s01",
                "layout": "layout_basic",
                "title": "概要",
                "bullets": [
                    {
                        "items": [
                            {"id": f"b{index}", "text": line, "level": 0}
                            for index, line in enumerate(body_lines, start=1)
                        ]
                    }
                ],
            }
        ],
    }
    return JobSpec.model_validate(payload)


def test_mapping_step_generates_rendering_outputs(tmp_path: Path) -> None:
    spec = _build_spec(["最初のポイント", "次のステップ"])
    context = PipelineContext(spec=spec, workdir=tmp_path)

    step = MappingStep(MappingOptions(output_dir=tmp_path))
    step.run(context)

    rendering_path = tmp_path / "rendering_ready.json"
    mapping_log_path = tmp_path / "mapping_log.json"

    assert rendering_path.exists()
    assert mapping_log_path.exists()

    rendering_payload = json.loads(rendering_path.read_text(encoding="utf-8"))
    slide = rendering_payload["slides"][0]

    assert slide["layout_id"] == "layout_basic"
    assert slide["elements"]["title"] == "概要"
    assert slide["elements"]["body"] == ["最初のポイント", "次のステップ"]
    assert slide["meta"]["page_no"] == 1
    assert slide["meta"]["fallback"] == "none"

    mapping_payload = json.loads(mapping_log_path.read_text(encoding="utf-8"))
    assert mapping_payload["meta"]["fallback_count"] == 0
    assert mapping_payload["meta"]["ai_patch_count"] == 0


def test_mapping_step_applies_fallback_when_body_overflow(tmp_path: Path) -> None:
    spec = _build_spec(["1行目", "2行目", "3行目"])
    context = PipelineContext(spec=spec, workdir=tmp_path)

    layouts_path = tmp_path / "layouts.jsonl"
    layouts_path.write_text(
        json.dumps(
            {
                "layout_id": "layout_basic",
                "usage_tags": ["overview"],
                "text_hint": {"max_lines": 2},
                "media_hint": {"allow_table": False},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    step = MappingStep(
        MappingOptions(
            output_dir=tmp_path,
            layouts_path=layouts_path,
        )
    )
    step.run(context)

    rendering_path = tmp_path / "rendering_ready.json"
    mapping_log_path = tmp_path / "mapping_log.json"
    fallback_report_path = tmp_path / "fallback_report.json"

    rendering_payload = json.loads(rendering_path.read_text(encoding="utf-8"))
    body = rendering_payload["slides"][0]["elements"]["body"]
    assert body == ["1行目", "2行目"], "最大行数に合わせて本文が縮約されること"
    assert rendering_payload["slides"][0]["meta"]["fallback"] == "shrink_text"

    mapping_payload = json.loads(mapping_log_path.read_text(encoding="utf-8"))
    slide_log = mapping_payload["slides"][0]
    assert slide_log["fallback"]["applied"] is True
    assert slide_log["fallback"]["history"] == ["shrink_text"]
    assert mapping_payload["meta"]["fallback_count"] == 1
    assert mapping_payload["meta"]["ai_patch_count"] == 1

    assert fallback_report_path.exists()
    report_payload = json.loads(fallback_report_path.read_text(encoding="utf-8"))
    assert report_payload["slides"][0]["slide_id"] == "s01"
