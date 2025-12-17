"""CardLayoutRecommender のユニットテスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

from pptx_generator.draft_recommender import (
    CardLayoutRecommender,
    CardLayoutRecommenderConfig,
    LayoutProfile,
)
from pptx_generator.settings.ai_policy import resolve_layout_ai_policy_path
from pptx_generator.layout_ai.client import LayoutAIResponse
from pptx_generator.models import (ContentElements, ContentSlide,
                                   ContentSlideSource, DraftAnalyzerSummary)


def _sample_slide(intent: str = "overview", *, with_source: bool = False) -> ContentSlide:
    source = None
    if with_source:
        source = ContentSlideSource(
            card_id="card-1",
            order=1,
            story_phase="introduction",
            intent_tags=("introduction",),
        )
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
        source=source,
    )


def test_recommend_returns_ai_boost_when_enabled() -> None:
    slide = _sample_slide()
    layouts = [
        LayoutProfile(
            layout_id="Title",
            layout_name="Title",
            usage_tags=("title", "overview"),
            text_hint={"max_lines": 3},
            media_hint={"allow_table": False},
        ),
        LayoutProfile(
            layout_id="Content",
            layout_name="Content",
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
            policy_path=resolve_layout_ai_policy_path().path,
        )
    )
    result = recommender.recommend(
        slide=slide,
        preferred_layout="Title",
        layouts=layouts,
        analyzer_summary=DraftAnalyzerSummary(severity_high=0, severity_medium=0, severity_low=0),
    )

    assert result.candidates, "候補が生成されるべき"
    assert len(result.candidates) == 1, "AI応答がある場合はトップ候補のみ返却されるべき"
    best_candidate, best_detail = result.candidates[0]
    assert best_candidate.layout_id in {"Title", "Content"}
    assert best_detail.ai_recommendation >= 0.0
    assert isinstance(result.ai_scores, dict)
    assert len(result.ai_scores) <= 1
    if result.ai_response is not None:
        assert result.ai_response.model
        assert isinstance(result.ai_response.recommended, list)
        assert len(result.ai_response.recommended) == 1
        recommended_layout_id, _ = result.ai_response.recommended[0]
        assert best_candidate.layout_id == recommended_layout_id


def test_recommend_without_ai_keeps_ai_score_zero() -> None:
    slide = _sample_slide(intent="problem")
    layouts = [
        LayoutProfile(
            layout_id="Problem",
            layout_name="Problem",
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
            layout_name="Content",
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


def test_ai_classification_overrides_usage_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    slide = _sample_slide(with_source=True)
    layouts = [
        LayoutProfile(
            layout_id="Content",
            layout_name="Content",
            usage_tags=("content",),
            text_hint={"max_lines": 5},
            media_hint={"allow_table": False},
        )
    ]

    config = CardLayoutRecommenderConfig(
        enable_ai=True,
        ai_weight=0.4,
        max_candidates=1,
        policy_path=Path("dummy-policy.json"),
    )
    recommender = CardLayoutRecommender(config)

    class FakePolicy:
        provider = "mock"
        model = "mock-layout"

        def resolve_prompt(self) -> str:
            return "classify layouts"

    class FakeClient:
        def recommend(self, request) -> LayoutAIResponse:
            assert request.card_payload.get("source", {}).get("card_id") == "card-1"
            detail = request.card_payload.get("allowed_tags_detail")
            assert detail is not None
            assert detail.get("content")
            return LayoutAIResponse(
                model="mock-layout",
                recommended=[("Content", 0.9)],
                reasons={"Content": "fits slide intent"},
                classifications={"Content": ("title", "overview")},
            )

    def fake_ensure(self) -> tuple[FakePolicy, FakeClient]:
        return FakePolicy(), FakeClient()

    monkeypatch.setattr(
        CardLayoutRecommender,
        "_ensure_layout_ai",
        fake_ensure,
        raising=False,
    )

    result = recommender.recommend(
        slide=slide,
        preferred_layout="Content",
        layouts=layouts,
        analyzer_summary=None,
    )

    assert result.classified_tags["Content"] == ("title", "overview")
    assert result.effective_tags["Content"] == ("title", "overview")
    assert "Content" not in result.ai_unknown_tags


def test_extract_slide_tags_includes_source_metadata() -> None:
    base_slide = _sample_slide(intent="", with_source=True)
    source = ContentSlideSource(
        card_id="card-1",
        order=base_slide.source.order if base_slide.source else None,
        story_phase="Introduction",
        intent_tags=("Overview", "Call_To_Action"),
        blueprint=None,
    )
    slide = base_slide.model_copy(
        update={
            "intent": "",
            "type_hint": None,
            "source": source,
        }
    )

    tags = CardLayoutRecommender._extract_slide_tags(slide)

    assert "overview" in tags
    assert "call_to_action" in tags


def test_build_layout_metadata_retains_stage1_payload() -> None:
    placeholder_summary = {
        "counts": {"title": 1, "body": 1},
        "area_ratio": {"title": 0.4, "body": 0.6},
        "details": [
            {"name": "Title", "type": "title", "area_ratio": 0.4},
            {"name": "Body", "type": "body", "area_ratio": 0.6},
        ],
        "attributes": {
            "total": 2,
            "has_title": True,
            "has_body": True,
            "has_table": False,
            "has_chart": False,
            "has_visual": False,
        },
    }
    blueprint = {
        "layout": "Sample",
        "slots": [
            {
                "slot_id": "sample.slot01",
                "anchor": "Title",
                "required": True,
                "content_type": "text",
                "intent_tags": ["overview"],
            }
        ],
    }
    meta = {"heuristic_reason": "placeholder:type=body"}
    layout_description = {
        "overview": "Sample Layout は本文メインの構成です。",
        "elements": [
            {
                "description": "中央に大きめの本文枠（Body）",
                "position": "中央",
                "size_label": "大きめ",
                "expects_text": True,
            }
        ],
    }

    profile = LayoutProfile(
        layout_id="sample-layout",
        layout_name="Sample Layout",
        usage_tags=("content",),
        text_hint={"max_lines": 4},
        media_hint={"allow_table": False},
        placeholder_summary=placeholder_summary,
        heuristic={"tags": ["content"], "reasons": ["placeholder:type=body"]},
        blueprint=blueprint,
        meta=meta,
        layout_description=layout_description,
    )

    metadata = CardLayoutRecommender._build_layout_metadata([profile])

    assert metadata["sample-layout"]["placeholder_summary"] == placeholder_summary
    assert metadata["sample-layout"]["blueprint"] == blueprint
    assert metadata["sample-layout"]["meta"] == meta
    assert metadata["sample-layout"]["heuristic"] == profile.heuristic
    assert metadata["sample-layout"]["layout_description"] == profile.layout_description
