"""Tests for layout loader helper utilities."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pptx_generator.pipeline.draft_structuring.errors import DraftStructuringError
from pptx_generator.pipeline.draft_structuring.layout_loader import (
    load_layouts,
    summarize_placeholders,
)


def test_load_layouts_reads_records_and_normalizes(tmp_path: Path) -> None:
    layout_file = tmp_path / "layouts.jsonl"
    layout_file.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "layout_id": "Title",
                        "layout_name": "Title Slide",
                        "usage_tags": ["title", "overview"],
                        "text_hint": {"max_lines": 3},
                        "media_hint": {"allow_table": False},
                        "placeholders": [
                            {"name": "Title", "type": "title", "bbox": {"width": 6, "height": 1.2}},
                            {"name": "Subtitle", "type": "subtitle", "bbox": {"width": 6, "height": 0.8}},
                        ],
                        "meta": {"layout_description": "Single column title"},
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "layout_id": "Content",
                        "usage_tags": ["content"],
                        "placeholders": [{"name": "Body", "type": "body"}],
                        "heuristic": {"score": 0.8},
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )

    layouts = load_layouts(path=layout_file, spec_source_path=None)

    assert len(layouts) == 2
    title_layout = layouts[0]
    assert title_layout.layout_name == "Title Slide"
    assert title_layout.usage_tags == ("title", "overview")
    # layout description should be normalized into dict form
    assert title_layout.layout_description == {"overview": "Single column title", "elements": []}
    summary = title_layout.placeholder_summary
    assert summary["counts"]["title"] == 1
    assert summary["counts"]["subtitle"] == 1
    assert summary["attributes"]["has_title"] is True

    content_layout = layouts[1]
    assert content_layout.usage_tags == ("content",)
    assert content_layout.heuristic == {"score": 0.8}


def test_load_layouts_raises_when_file_missing(tmp_path: Path) -> None:
    missing = tmp_path / "not_found.jsonl"
    with pytest.raises(DraftStructuringError):
        load_layouts(path=missing, spec_source_path=None)


def test_load_layouts_invalid_json(tmp_path: Path) -> None:
    layout_file = tmp_path / "layouts.jsonl"
    layout_file.write_text("{invalid-json", encoding="utf-8")
    with pytest.raises(DraftStructuringError):
        load_layouts(path=layout_file, spec_source_path=None)


def test_summarize_placeholders_computes_area_ratios() -> None:
    summary = summarize_placeholders(
        [
            {"name": "Body", "type": "body", "bbox": {"width": 6, "height": 3}},
            {"name": "Chart", "type": "chart", "bbox": {"width": 3, "height": 3}, "flags": ["visual"]},
            {"type": "body"},
        ]
    )

    # two body placeholders and one chart, chart should receive an entry
    assert summary["counts"]["body"] == 2
    assert summary["counts"]["chart"] == 1
    assert summary["attributes"]["has_chart"] is True
    chart_entries = [item for item in summary["details"] if item["type"] == "chart"]
    assert chart_entries[0]["name"] == "Chart"
