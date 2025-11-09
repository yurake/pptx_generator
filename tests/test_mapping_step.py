"""マッピングステップのユニットテスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pptx_generator.models import JobSpec
from pptx_generator.pipeline.base import PipelineContext
from pptx_generator.pipeline.mapping import MappingOptions, MappingStep
from pptx_generator.brief import BriefCard, BriefDocument, BriefStoryContext, BriefStoryInfo


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


def test_mapping_step_generates_generate_ready_outputs(tmp_path: Path) -> None:
    spec = _build_spec(["最初のポイント", "次のステップ"])
    context = PipelineContext(spec=spec, workdir=tmp_path)
    template_path = tmp_path / "template.pptx"
    template_path.write_bytes(b"")
    brief_doc = BriefDocument(
        brief_id="brief-test",
        cards=[
            BriefCard(
                card_id="s01",
                chapter="概要",
                message="概要のポイント",
                narrative=["最初のポイント", "次のステップ"],
                supporting_points=[],
                story=BriefStoryInfo(phase="introduction"),
                intent_tags=["overview"],
            )
        ],
        story_context=BriefStoryContext(chapters=[]),
    )
    context.add_artifact("brief_document", brief_doc)

    step = MappingStep(
        MappingOptions(
            output_dir=tmp_path,
            template_path=template_path,
        )
    )
    step.run(context)

    generate_ready_path = tmp_path / "generate_ready.json"
    mapping_log_path = tmp_path / "mapping_log.json"

    assert generate_ready_path.exists()
    assert mapping_log_path.exists()

    generate_ready_payload = json.loads(generate_ready_path.read_text(encoding="utf-8"))
    slide = generate_ready_payload["slides"][0]

    assert slide["layout_id"] == "layout_basic"
    assert slide["elements"]["title"] == "概要"
    assert slide["elements"]["body"] == ["最初のポイント", "次のステップ"]
    assert slide["meta"]["page_no"] == 1
    assert slide["meta"]["fallback"] == "none"
    meta_payload = generate_ready_payload["meta"]
    assert meta_payload["job_meta"]["title"] == "テスト資料"
    assert meta_payload["job_auth"]["created_by"] == "tester"
    assert meta_payload["template_path"] == template_path.name

    mapping_payload = json.loads(mapping_log_path.read_text(encoding="utf-8"))
    assert mapping_payload["meta"]["fallback_count"] == 0
    assert mapping_payload["meta"]["ai_patch_count"] == 0
    assert mapping_payload["meta"]["analyzer_issue_count"] == 0
    assert mapping_payload["meta"]["analyzer_issue_counts_by_type"] == {}
    assert mapping_payload["meta"]["analyzer_issue_counts_by_severity"] == {}

    analyzer_summary = mapping_payload["slides"][0]["analyzer"]
    assert analyzer_summary["issue_count"] == 0
    assert analyzer_summary["issues"] == []


def test_mapping_step_applies_fallback_when_body_overflow(tmp_path: Path) -> None:
    spec = _build_spec(["1行目", "2行目", "3行目"])
    context = PipelineContext(spec=spec, workdir=tmp_path)
    template_path = tmp_path / "template.pptx"
    template_path.write_bytes(b"")
    brief_doc = BriefDocument(
        brief_id="brief-test",
        cards=[
            BriefCard(
                card_id="s01",
                chapter="概要",
                message="概要のポイント",
                narrative=["1行目", "2行目", "3行目"],
                supporting_points=[],
                story=BriefStoryInfo(phase="introduction"),
                intent_tags=["overview"],
            )
        ],
        story_context=BriefStoryContext(chapters=[]),
    )
    context.add_artifact("brief_document", brief_doc)

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
            template_path=template_path,
        )
    )
    step.run(context)

    generate_ready_path = tmp_path / "generate_ready.json"
    mapping_log_path = tmp_path / "mapping_log.json"
    fallback_report_path = tmp_path / "fallback_report.json"

    generate_ready_payload = json.loads(generate_ready_path.read_text(encoding="utf-8"))
    body = generate_ready_payload["slides"][0]["elements"]["body"]
    assert body == ["1行目", "2行目"], "最大行数に合わせて本文が縮約されること"
    assert generate_ready_payload["slides"][0]["meta"]["fallback"] == "shrink_text"
    assert generate_ready_payload["meta"]["template_path"] == template_path.name

    mapping_payload = json.loads(mapping_log_path.read_text(encoding="utf-8"))
    slide_log = mapping_payload["slides"][0]
    assert slide_log["fallback"]["applied"] is True
    assert slide_log["fallback"]["history"] == ["shrink_text"]
    assert slide_log["analyzer"]["issue_count"] == 0
    assert mapping_payload["meta"]["fallback_count"] == 1
    assert mapping_payload["meta"]["ai_patch_count"] == 1
    assert mapping_payload["meta"]["analyzer_issue_count"] == 0

    assert fallback_report_path.exists()
    report_payload = json.loads(fallback_report_path.read_text(encoding="utf-8"))
    assert report_payload["slides"][0]["slide_id"] == "s01"
