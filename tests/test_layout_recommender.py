"""CardLayoutRecommender のユニットテスト。"""

from __future__ import annotations

from pathlib import Path

from pptx_generator.draft_recommender import (
    CardLayoutRecommender,
    CardLayoutRecommenderConfig,
    LayoutProfile,
)
from pptx_generator.models import ContentElements, ContentSlide, DraftAnalyzerSummary


def _sample_slide(intent: str = "overview") -> ContentSlide:
    return ContentSlide(
        id="slide-1",
        intent=intent,
        type_hint="content",
        elements=ContentElements(
            title="製品概要",
            body=["主な特徴", "市場インパクト"],
            note=None,
            table_data=None,
        ),
    )


def test_recommend_returns_ai_boost_when_enabled() -> None:
    slide = _sample_slide()
    layouts = [
        LayoutProfile(
            layout_id="Title",
            usage_tags=("title", "overview"),
            text_hint={"max_lines": 3},
            media_hint={"allow_table": False},
        ),
        LayoutProfile(
            layout_id="Content",
            usage_tags=("content",),
            text_hint={"max_lines": 6},
            media_hint={"allow_table": True},
        ),
    ]

    recommender = CardLayoutRecommender(
        CardLayoutRecommenderConfig(
            enable_ai=True,
            ai_weight=0.3,
            max_candidates=2,
            policy_path=Path("config/layout_ai_policies.json"),
        )
    )
    result = recommender.recommend(
        slide=slide,
        preferred_layout="Title",
        layouts=layouts,
        analyzer_summary=DraftAnalyzerSummary(severity_high=0, severity_medium=0, severity_low=0),
    )

    assert result.candidates, "候補が生成されるべき"
    best_candidate, best_detail = result.candidates[0]
    assert best_candidate.layout_id in {"Title", "Content"}
    assert best_detail.ai_recommendation >= 0.0
    assert isinstance(result.ai_scores, dict)
    if result.ai_response is not None:
        assert result.ai_response.model
        assert isinstance(result.ai_response.recommended, list)


def test_recommend_without_ai_keeps_ai_score_zero() -> None:
    slide = _sample_slide(intent="problem")
    layouts = [
        LayoutProfile(
            layout_id="Problem",
            usage_tags=("problem",),
            text_hint={},
            media_hint={},
        )
    ]

    recommender = CardLayoutRecommender(
        CardLayoutRecommenderConfig(enable_ai=False, max_candidates=1)
    )
    result = recommender.recommend(
        slide=slide,
        preferred_layout="Problem",
        layouts=layouts,
        analyzer_summary=None,
    )

    assert result.candidates
    _, detail = result.candidates[0]
    assert detail.ai_recommendation == 0.0


def test_layout_ai_missing_policy_falls_back_to_simulation(tmp_path) -> None:
    slide = _sample_slide()
    layouts = [
        LayoutProfile(
            layout_id="Content",
            usage_tags=("content",),
            text_hint={},
            media_hint={},
        )
    ]

    config = CardLayoutRecommenderConfig(
        enable_ai=True,
        ai_weight=0.2,
        max_candidates=1,
        policy_path=tmp_path / "not-found.json",
        enable_simulated_ai=True,
    )
    recommender = CardLayoutRecommender(config)
    result = recommender.recommend(
        slide=slide,
        preferred_layout="Content",
        layouts=layouts,
        analyzer_summary=None,
    )

    assert result.candidates
    _, detail = result.candidates[0]
    assert detail.ai_recommendation > 0.0
