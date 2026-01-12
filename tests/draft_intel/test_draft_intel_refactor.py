from __future__ import annotations

import json
from pathlib import Path

from pptx_generator.draft import (
    ChapterTemplate,
    ChapterTemplateSection,
    evaluate_chapter_template,
    load_analysis_summary,
    load_chapter_template,
)


def test_evaluate_chapter_template_reports_optional_excess_and_capacity() -> None:
    template = ChapterTemplate(
        template_id="tpl",
        name="tpl",
        structure_pattern="custom",
        required_sections=(ChapterTemplateSection("intro", min_slides=1, max_slides=2),),
        optional_sections=(ChapterTemplateSection("appendix", max_slides=1),),
        max_main_pages=2,
        appendix_policy="block",
        tags=(),
    )

    result = evaluate_chapter_template(
        template=template,
        section_counts={"intro": 2, "appendix": 2},
        total_main_pages=3,
    )

    assert result.match_score == 1.0
    assert result.section_scores["intro"] == 1.0
    assert result.section_scores["appendix"] == 0.5
    issues = {(m.section_id, m.issue, m.severity) for m in result.mismatches}
    assert ("appendix", "excess", "warn") in issues
    assert ("__capacity__", "capacity", "blocker") in issues


def test_evaluate_chapter_template_reports_capacity_warn() -> None:
    template = ChapterTemplate(
        template_id="tpl",
        name="tpl",
        structure_pattern="custom",
        required_sections=(),
        optional_sections=(),
        max_main_pages=1,
        appendix_policy="overflow",
        tags=(),
    )

    result = evaluate_chapter_template(
        template=template,
        section_counts={},
        total_main_pages=2,
    )

    assert result.match_score == 1.0
    assert [(m.section_id, m.issue, m.severity) for m in result.mismatches] == [
        ("__capacity__", "capacity", "warn")
    ]


def test_evaluate_chapter_template_marks_required_missing() -> None:
    template = ChapterTemplate(
        template_id="tpl",
        name="tpl",
        structure_pattern="custom",
        required_sections=(ChapterTemplateSection("intro", min_slides=1),),
        optional_sections=(),
    )

    result = evaluate_chapter_template(
        template=template,
        section_counts={},
        total_main_pages=0,
    )

    assert result.match_score == 0.0
    assert result.section_scores["intro"] == 0.0
    assert [(m.section_id, m.issue) for m in result.mismatches] == [
        ("intro", "missing")
    ]


def test_evaluate_chapter_template_marks_required_insufficient() -> None:
    template = ChapterTemplate(
        template_id="tpl",
        name="tpl",
        structure_pattern="custom",
        required_sections=(ChapterTemplateSection("intro", min_slides=2),),
        optional_sections=(),
    )

    result = evaluate_chapter_template(
        template=template,
        section_counts={"intro": 1},
        total_main_pages=1,
    )

    assert result.match_score == 0.0
    assert result.section_scores["intro"] == 0.5
    assert [(m.section_id, m.issue, m.severity) for m in result.mismatches] == [
        ("intro", "insufficient", "blocker")
    ]


def test_evaluate_chapter_template_optional_zero_sets_score_zero() -> None:
    template = ChapterTemplate(
        template_id="tpl",
        name="tpl",
        structure_pattern="custom",
        required_sections=(),
        optional_sections=(ChapterTemplateSection("appendix", max_slides=2),),
    )

    result = evaluate_chapter_template(
        template=template,
        section_counts={},
        total_main_pages=0,
    )

    assert result.section_scores["appendix"] == 0.0
    assert result.mismatches == []


def test_load_analysis_summary_parses_entries(tmp_path: Path) -> None:
    payload = {
        "slides": [
            {
                "slide_uid": "s1",
                "severity_counts": {"high": 1, "medium": 0, "low": 2},
                "layout_consistency": "OK",
                "blocking_tags": ["tag1", " "],
            },
            {
                "slide_uid": "s2",
                "severity_counts": {},
                "layout_consistency": "unknown",
                "blocking_tags": "not-a-list",
            },
            {},
        ]
    }
    path = tmp_path / "analysis_summary.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    summary = load_analysis_summary(path)

    assert set(summary) == {"s1", "s2"}
    assert summary["s1"].severity_high == 1
    assert summary["s1"].severity_low == 2
    assert summary["s1"].layout_consistency == "ok"
    assert summary["s1"].blocking_tags == ("tag1",)
    assert summary["s2"].layout_consistency is None
    assert summary["s2"].blocking_tags == ()


def test_load_analysis_summary_normalizes_non_string_layout_and_blocking_tags(tmp_path: Path) -> None:
    payload = {
        "slides": [
            {
                "slide_uid": "s1",
                "severity_counts": {},
                "layout_consistency": 123,
                "blocking_tags": None,
            }
        ]
    }
    path = tmp_path / "analysis_summary.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    summary = load_analysis_summary(path)

    assert summary["s1"].layout_consistency is None
    assert summary["s1"].blocking_tags == ()


def test_load_chapter_template_parses_constraints(tmp_path: Path) -> None:
    base_dir = tmp_path / "templates"
    base_dir.mkdir()
    template_path = base_dir / "custom.json"
    template_path.write_text(
        json.dumps(
            {
                "template_id": "custom",
                "name": "Custom Template",
                "structure_pattern": "custom",
                "required_sections": [{"id": "intro", "min_slides": 1, "max_slides": 2}],
                "optional_sections": [{"id": "appendix", "max_slides": 1}],
                "constraints": {
                    "max_main_pages": 10,
                    "appendix_policy": "block",
                    "tags": ["alpha", ""],
                },
            }
        ),
        encoding="utf-8",
    )

    template = load_chapter_template(base_dir, "custom")

    assert template is not None
    assert template.max_main_pages == 10
    assert template.appendix_policy == "block"
    assert template.tags == ("alpha",)
    assert template.required_sections[0].section_id == "intro"
