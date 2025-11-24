"""マッピングステップのユニットテスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pptx_generator.models import (
    ContentApprovalDocument,
    ContentDocumentMeta,
    ContentElements,
    ContentSlide,
    ContentTableData,
    DraftDocument,
    DraftSection,
    DraftSlideCard,
    GenerateReadyDocument,
    JobSpec,
    JobMeta,
    JobAuth,
    Slide,
    SlideTable,
)
from pptx_generator.pipeline.base import PipelineContext
from pptx_generator.pipeline.mapping import MappingOptions, MappingStep
from pptx_generator.prepare import (
    PrepareBodyBlock,
    PrepareCard,
    PrepareCardContent,
    PrepareCardRole,
    PrepareDocument,
    PrepareStoryContext,
)


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
    prepare_doc = PrepareDocument(
        prepare_id="prepare-test",
        cards=[
            PrepareCard(
                card_id="s01",
                order=1,
                role=PrepareCardRole(story_phase="introduction", intent_tags=["overview"]),
                content=PrepareCardContent(
                    headline="概要",
                    subtitle="サブタイトル",
                    body=[
                        PrepareBodyBlock(type="paragraph", text="最初のポイント"),
                        PrepareBodyBlock(type="paragraph", text="次のステップ"),
                    ],
                ),
            )
        ],
        story_context=PrepareStoryContext(chapters=[]),
    )
    context.add_artifact("prepare_document", prepare_doc)

    content_document = ContentApprovalDocument(
        slides=[
            ContentSlide(
                id="s01",
                intent="overview",
                type_hint="introduction",
                elements=ContentElements(
                    title="概要",
                    subtitle="サブタイトル",
                    body=["最初のポイント", "次のステップ"],
                    table_data=None,
                    note=None,
                ),
                status="approved",
            )
        ],
        meta=ContentDocumentMeta(tone=None),
    )
    context.add_artifact("content_approved", content_document)

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
    assert slide["elements"]["subtitle"] == "サブタイトル"
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
    prepare_doc = PrepareDocument(
        prepare_id="prepare-test",
        cards=[
            PrepareCard(
                card_id="s01",
                order=1,
                role=PrepareCardRole(story_phase="introduction", intent_tags=["overview"]),
                content=PrepareCardContent(
                    headline="概要",
                    body=[
                        PrepareBodyBlock(type="paragraph", text="1行目"),
                        PrepareBodyBlock(type="paragraph", text="2行目"),
                        PrepareBodyBlock(type="paragraph", text="3行目"),
                    ],
                ),
            )
        ],
        story_context=PrepareStoryContext(chapters=[]),
    )
    context.add_artifact("prepare_document", prepare_doc)

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
    assert body == ["1行目", "2行目", "3行目"], "オーバーフロー時でも本文は維持されること"
    assert generate_ready_payload["slides"][0]["meta"]["fallback"] == "none"
    assert generate_ready_payload["meta"]["template_path"] == template_path.name

    mapping_payload = json.loads(mapping_log_path.read_text(encoding="utf-8"))
    slide_log = mapping_payload["slides"][0]
    assert slide_log["fallback"]["applied"] is False
    assert slide_log["fallback"]["history"] == []
    assert slide_log["analyzer"]["issue_count"] == 0
    assert mapping_payload["meta"]["fallback_count"] == 0
    assert mapping_payload["meta"]["ai_patch_count"] == 0
    assert mapping_payload["meta"]["analyzer_issue_count"] == 0
    assert slide_log["warnings"] == [
        "body が許容行数 2 を超過しています（現在 3 行）"
    ]

    assert not fallback_report_path.exists()


def test_mapping_step_assigns_table_anchor(tmp_path: Path) -> None:
    layouts_path = tmp_path / "layouts.jsonl"
    layouts_path.write_text(
        json.dumps(
            {
                "layout_id": "two_column_detail",
                "layout_name": "Two Column Detail",
                "usage_tags": ["content"],
                "text_hint": {"max_lines": 4},
                "media_hint": {"allow_table": True},
                "placeholders": [
                    {
                        "name": "Body Left",
                        "type": "object",
                        "bbox": {"x": 0, "y": 0, "width": 1000000, "height": 1000000},
                    },
                    {
                        "name": "Body Right",
                        "type": "object",
                        "bbox": {"x": 1200000, "y": 0, "width": 1200000, "height": 1000000},
                    },
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    spec = JobSpec(
        meta=JobMeta(schema_version="1.0", title="テーブル検証"),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="slide-1",
                layout="two_column_detail",
                title="テーブルページ",
                tables=[
                    SlideTable(
                        id="tbl-legacy",
                        anchor="Body Right",
                        columns=["旧指標"],
                        rows=[["80件/月"]],
                    )
                ],
            )
        ],
    )
    context = PipelineContext(spec=spec, workdir=tmp_path)

    draft_card = DraftSlideCard(ref_id="slide-1", order=1, layout_hint="two_column_detail")
    draft_section = DraftSection(name="Main", order=1, slides=[draft_card])
    draft_document = DraftDocument(sections=[draft_section])
    context.add_artifact("draft_document", draft_document)

    content_slide = ContentSlide(
        id="slide-1",
        intent="overview",
        elements=ContentElements(
            title="テーブルページ",
            body=["主要指標"],
            table_data=ContentTableData(headers=["指標"], rows=[["120件/月"]]),
        ),
        status="approved",
    )
    content_document = ContentApprovalDocument(
        slides=[content_slide],
        meta=ContentDocumentMeta(),
    )
    context.add_artifact("content_approved", content_document)

    output_dir = tmp_path / "mapping-output"
    options = MappingOptions(
        output_dir=output_dir,
        layouts_path=layouts_path,
    )
    step = MappingStep(options)
    step.run(context)

    generate_ready: GenerateReadyDocument = context.artifacts["generate_ready"]
    slide_elements = generate_ready.slides[0].elements
    assert "Body Right" in slide_elements
    assert slide_elements["Body Right"]["rows"] == [["120件/月"]]
    assert "table" not in slide_elements
