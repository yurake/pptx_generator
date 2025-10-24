from pathlib import Path

import pytest

from pptx_generator.draft_intel import (
    ChapterTemplate,
    ChapterTemplateSection,
    clamp_score_detail,
    compute_analyzer_support,
    evaluate_chapter_template,
    load_analysis_summary,
    summarize_analyzer_counts,
)
from pptx_generator.models import DraftAnalyzerSummary, DraftLayoutScoreDetail, DraftTemplateMismatch


class TestChapterTemplateEvaluation:
    def test_evaluate_template(self) -> None:
        template = ChapterTemplate(
            template_id="sample",
            name="Sample",
            structure_pattern="report",
            required_sections=(
                ChapterTemplateSection(section_id="intro", min_slides=1, max_slides=2),
                ChapterTemplateSection(section_id="solution", min_slides=2, max_slides=4),
            ),
            optional_sections=(
                ChapterTemplateSection(section_id="appendix", min_slides=0, max_slides=3),
            ),
            max_main_pages=5,
            appendix_policy="overflow",
            tags=("bp",),
        )

        evaluation = evaluate_chapter_template(
            template=template,
            section_counts={"intro": 1, "solution": 2, "appendix": 1},
            total_main_pages=4,
        )

        assert pytest.approx(evaluation.match_score) == 1.0
        assert evaluation.section_scores["intro"] == 1.0
        assert evaluation.section_scores["solution"] == 1.0
        assert len(evaluation.mismatches) == 0

    def test_evaluate_template_with_mismatch(self) -> None:
        template = ChapterTemplate(
            template_id="sample",
            name="Sample",
            structure_pattern="report",
            required_sections=(
                ChapterTemplateSection(section_id="intro", min_slides=1, max_slides=1),
            ),
            optional_sections=(),
            max_main_pages=2,
            appendix_policy="block",
            tags=(),
        )

        evaluation = evaluate_chapter_template(
            template=template,
            section_counts={"intro": 0},
            total_main_pages=3,
        )

        assert evaluation.match_score == 0.0
        assert any(isinstance(mismatch, DraftTemplateMismatch) for mismatch in evaluation.mismatches)
        capacity_issue = [m for m in evaluation.mismatches if m.issue == "capacity"]
        assert capacity_issue and capacity_issue[0].severity == "blocker"


class TestAnalyzerUtilities:
    def test_compute_analyzer_support(self) -> None:
        assert compute_analyzer_support(None) == 0.0
        summary = DraftAnalyzerSummary(severity_high=1)
        assert compute_analyzer_support(summary) == -0.2
        summary = DraftAnalyzerSummary(severity_high=0, severity_medium=1)
        assert compute_analyzer_support(summary) == -0.1
        summary = DraftAnalyzerSummary(severity_high=0, severity_medium=0, severity_low=2)
        assert compute_analyzer_support(summary) == 0.1

    def test_clamp_score_detail(self) -> None:
        detail = DraftLayoutScoreDetail(uses_tag=0.5, content_capacity=0.5, diversity=0.5, analyzer_support=0.5)
        clamped = clamp_score_detail(detail)
        assert clamped.total <= 1.0 + 1e-6

    def test_load_analysis_summary(self, tmp_path: Path) -> None:
        path = tmp_path / "analysis_summary.json"
        path.write_text(
            """
            {
              "slides": [
                {
                  "slide_uid": "s01",
                  "severity_counts": {"high": 1, "medium": 0, "low": 0},
                  "layout_consistency": "warn",
                  "blocking_tags": ["layout_consistency"]
                }
              ]
            }
            """,
            encoding="utf-8",
        )

        summary = load_analysis_summary(path)
        assert "s01" in summary
        assert summary["s01"].severity_high == 1
        assert summary["s01"].layout_consistency == "warn"

    def test_summarize_analyzer_counts(self) -> None:
        entries = [
            DraftAnalyzerSummary(severity_high=1, severity_medium=2, severity_low=0),
            DraftAnalyzerSummary(severity_high=0, severity_medium=1, severity_low=3),
        ]
        totals = summarize_analyzer_counts(entries)
        assert totals == {"high": 1, "medium": 3, "low": 3}
