"""generate_ready ユーティリティのテスト。"""

from __future__ import annotations

import pytest

from pptx_generator.models import (JobAuth, JobMeta, MappingSlideMeta,
                                   GenerateReadyDocument,
                                   GenerateReadyMeta, GenerateReadySlide)
from pptx_generator.generate_ready import generate_ready_to_jobspec


def test_generate_ready_to_jobspec_conversion() -> None:
    document = GenerateReadyDocument(
        slides=[
            GenerateReadySlide(
                layout_id="layout_basic",
                layout_name="Layout Basic Human",
                elements={
                    "title": "タイトル",
                    "subtitle": "サブタイトル",
                    "note": "ノートです",
                    "body": ["a", "b"],
                    "custom_anchor": ["anchored"],
                    "table_anchor": {"headers": ["H1"], "rows": [["R1"]]},
                    "image_anchor": {"source": "https://example.com/img.png", "sizing": "fit"},
                    "chart_anchor": {
                        "type": "bar",
                        "categories": ["Q1", "Q2"],
                        "series": [{"name": "シリーズA", "values": [1, 2]}],
                    },
                    "textbox_anchor": {"text": "テキストボックス"},
                },
                meta=MappingSlideMeta(
                    section="Overview",
                    page_no=1,
                    sources=["slide-1"],
                    fallback="none",
                ),
            )
        ],
        meta=GenerateReadyMeta(
            template_version="v1",
            content_hash="sha256:abc",
            generated_at="2025-10-18T00:00:00Z",
            job_meta=JobMeta(
                schema_version="1.0",
                title="資料タイトル",
                client="Client A",
                author="Author A",
                created_at="2025-10-18",
                theme="corporate",
                locale="ja-JP",
            ),
            job_auth=JobAuth(created_by="tester", department="DX"),
        ),
    )

    spec = generate_ready_to_jobspec(document)

    assert spec.meta.title == "資料タイトル"
    assert spec.auth.created_by == "tester"
    assert len(spec.slides) == 1

    slide = spec.slides[0]
    assert slide.id == "slide-1"
    assert slide.layout == "Layout Basic Human"
    assert slide.title == "タイトル"
    assert slide.subtitle == "サブタイトル"
    assert slide.notes == "ノートです"

    assert len(slide.bullets) >= 2
    body_group = next(group for group in slide.bullets if group.anchor is None)
    assert [bullet.text for bullet in body_group.items] == ["a", "b"]
    anchored_group = next(group for group in slide.bullets if group.anchor == "custom_anchor")
    assert [bullet.text for bullet in anchored_group.items] == ["anchored"]

    table = slide.tables[0]
    assert table.anchor == "table_anchor"
    assert table.columns == ["H1"]
    assert table.rows == [["R1"]]

    image = slide.images[0]
    assert image.anchor == "image_anchor"
    assert image.source == "https://example.com/img.png"

    chart = slide.charts[0]
    assert chart.anchor == "chart_anchor"
    assert chart.type == "bar"
    assert chart.categories == ["Q1", "Q2"]
    assert chart.series[0].values == [1, 2]

    textbox = slide.textboxes[0]
    assert textbox.anchor == "textbox_anchor"
    assert textbox.text == "テキストボックス"


def test_generate_ready_to_jobspec_defaults() -> None:
    document = GenerateReadyDocument(
        slides=[
            GenerateReadySlide(
                layout_id="layout_basic",
                layout_name=None,
                elements={},
                meta=MappingSlideMeta(
                    section=None,
                    page_no=1,
                    sources=[],
                    fallback="none",
                ),
            )
        ],
        meta=GenerateReadyMeta(
            template_version=None,
            content_hash=None,
            generated_at="2025-10-18T00:00:00Z",
            job_meta=None,
            job_auth=None,
        ),
    )

    spec = generate_ready_to_jobspec(document)

    assert spec.meta.title == "Untitled Deck"
    assert spec.meta.schema_version == "unknown"
    assert spec.meta.created_at == "2025-10-18T00:00:00Z"
    assert spec.auth.created_by == "unknown"
    assert len(spec.slides) == 1
    slide = spec.slides[0]
    assert slide.id == "slide-1"
    assert slide.layout == "layout_basic"


def test_generate_ready_to_jobspec_respects_auto_draw() -> None:
    document = GenerateReadyDocument(
        slides=[
            GenerateReadySlide(
                layout_id="layout_basic",
                layout_name="Layout Basic",
                elements={"title": "タイトル"},
                meta=MappingSlideMeta(
                    section=None,
                    page_no=1,
                    sources=["slide-1"],
                    fallback="none",
                    auto_draw=[{"anchor": "Num", "left_in": 9.0, "top_in": 6.5, "width_in": 1.0, "height_in": 0.4}],
                ),
            )
        ],
        meta=GenerateReadyMeta(
            template_version=None,
            content_hash=None,
            generated_at="2025-10-18T00:00:00Z",
            job_meta=None,
            job_auth=None,
        ),
    )

    spec = generate_ready_to_jobspec(document)

    slide = spec.slides[0]
    assert slide.auto_draw_anchors == ["Num"]
    assert "Num" in slide.auto_draw_boxes
    box = slide.auto_draw_boxes["Num"]
    assert box.left_in == pytest.approx(9.0)
