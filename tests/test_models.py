"""モデル定義のテスト。"""

from __future__ import annotations

import pytest

from pptx_generator.models import (AIReviewResult, AutoFixProposal,
                                   ChartOptions, ChartSeries, ContentApprovalDocument,
                                   ContentElements, ContentReviewLogEntry,
                                   ContentSlide, ContentTableData, JobAuth,
                                   JobMeta, JobSpec, JsonPatchOperation, Slide,
                                   SlideChart, SlideTable, TableStyle)


def test_job_spec_accepts_tables_and_charts() -> None:
    spec = JobSpec(
        meta=JobMeta(schema_version="1.0", title="提案書"),
        auth=JobAuth(created_by="tester"),
        slides=[
            Slide(
                id="slide-1",
                layout="Title and Content",
                tables=[
                    SlideTable(
                        id="table-1",
                        columns=["項目", "値"],
                        rows=[["A", 1], ["B", 2]],
                        style=TableStyle(header_fill="#112233", zebra=True),
                    )
                ],
                charts=[
                    SlideChart(
                        id="chart-1",
                        type="column",
                        categories=["Before", "After"],
                        series=[
                            ChartSeries(name="効果", values=[10, 5], color_hex="#abcdef"),
                        ],
                        options=ChartOptions(data_labels=True, y_axis_format="{0}%"),
                    )
                ],
            )
        ],
    )

    table = spec.slides[0].tables[0]
    chart = spec.slides[0].charts[0]

    assert table.style is not None
    assert table.style.header_fill == "#112233"
    assert chart.series[0].color_hex == "#abcdef"
    assert chart.options is not None
    assert chart.options.data_labels is True


def test_content_elements_body_constraints() -> None:
    elements = ContentElements(
        title="市場環境の変化",
        body=["短文1", "短文2"],
        table_data=ContentTableData(
            headers=["指標", "前年比"],
            rows=[["売上", "112%"], ["利益", "108%"]],
        ),
    )

    assert len(elements.body) == 2
    with pytest.raises(ValueError):
        ContentElements(title="NG", body=["a" * 41])
    with pytest.raises(ValueError):
        ContentElements(title="NG", body=["a"] * 7)


def test_json_patch_operation_requires_absolute_path() -> None:
    operation = JsonPatchOperation(op="replace", path="/elements/title", value="更新")
    assert operation.path == "/elements/title"
    proposal = AutoFixProposal(
        patch_id="p01", description="タイトル更新", patch=[operation]
    )
    assert len(proposal.patch) == 1

    with pytest.raises(ValueError):
        JsonPatchOperation(op="replace", path="elements/title", value="更新")


def test_content_approval_document_validation() -> None:
    document = ContentApprovalDocument(
        slides=[
            ContentSlide(
                id="s01",
                intent="市場動向",
                status="approved",
                elements=ContentElements(title="市場", body=["需要は増加"]),
                ai_review=AIReviewResult(grade="A"),
                applied_autofix=["p01"],
            )
        ]
    )

    document.ensure_all_approved()

    with pytest.raises(ValueError):
        ContentApprovalDocument(
            slides=[
                ContentSlide(
                    id="s02",
                    intent="提案価値",
                    status="draft",
                    elements=ContentElements(title="提案", body=["価値"]),
                )
            ]
        ).ensure_all_approved()


def test_content_review_log_entry_parses_timestamp() -> None:
    entry = ContentReviewLogEntry(
        slide_id="s01",
        action="approve",
        actor="editor@example.com",
        timestamp="2025-10-17T10:00:00+09:00",
        applied_autofix=["p01"],
        ai_grade="A",
    )

    assert entry.timestamp.tzinfo is not None
