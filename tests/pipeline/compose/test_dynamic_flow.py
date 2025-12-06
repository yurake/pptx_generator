from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from pptx_generator.draft_recommender import LayoutProfile, RecommendationResult
from pptx_generator.layout_ai.client import LayoutAIResponse
from pptx_generator.models import (
    ContentElements,
    ContentSlide,
    DraftLayoutCandidate,
    DraftLayoutScoreDetail,
    DraftSection,
    DraftSlideCard,
    Slide,
)
from pptx_generator.pipeline.draft_structuring.dynamic_flow import (
    DraftAccumulator,
    DraftStructuringOptions,
    DraftWorkItem,
    _process_work_item,
    _resolve_section,
)


class _FakeRecommender:
    def __init__(self, recommendation: RecommendationResult) -> None:
        self._recommendation = recommendation

    def recommend(
        self,
        *,
        slide: ContentSlide,
        preferred_layout: str,
        layouts,
        analyzer_summary=None,
    ) -> RecommendationResult:
        return self._recommendation


def _make_candidate(layout_id: str, score: float, ai_recommendation: float) -> tuple[Any, DraftLayoutScoreDetail]:
    detail = DraftLayoutScoreDetail(
        uses_tag=0.2,
        content_capacity=0.3,
        diversity=0.1,
        analyzer_support=0.2,
        ai_recommendation=ai_recommendation,
    )
    return DraftLayoutCandidate(layout_id=layout_id, score=score), detail


def _base_content_slide() -> ContentSlide:
    return ContentSlide(
        id="slide-1",
        intent="introduction",
        elements=ContentElements(title="Intro", body=["Summary"]),
    )


def _base_layout_profile(layout_id: str) -> LayoutProfile:
    return LayoutProfile(
        layout_id=layout_id,
        layout_name=f"{layout_id}-name",
        usage_tags=("intro",),
        text_hint={},
        media_hint={},
        meta={"heuristic_reason": "auto"},
        blueprint={"id": f"bp-{layout_id}"},
    )


def test_process_work_item_creates_section_and_mapping_log() -> None:
    recommendation = RecommendationResult(
        candidates=[_make_candidate("Title", 0.9, 0.6)],
        ai_scores={"Title": 0.8},
        ai_response=None,
        classified_tags={"Title": ("intro",)},
        effective_tags={"Title": ("intro",)},
        baseline_tags={"Title": ("intro",)},
        ai_unknown_tags={},
    )
    recommender = _FakeRecommender(recommendation)
    accumulator = DraftAccumulator()
    options = DraftStructuringOptions()
    content_slide = _base_content_slide()
    spec_slide = Slide(id="slide-1", layout="Title")
    layout_profile = _base_layout_profile("Title")

    _process_work_item(
        options=options,
        item=DraftWorkItem(content_slide=content_slide, spec_slide=spec_slide),
        accumulator=accumulator,
        analyzer_map={},
        recommender=recommender,
        layout_lookup={"Title": layout_profile},
        tag_detail_map={"intro": {"label": "Introduction"}},
        layouts=[layout_profile],
    )

    assert len(accumulator.sections) == 1
    section = accumulator.sections[0]
    assert section.name == "Intent: introduction"
    assert isinstance(section, DraftSection)
    assert len(section.slides) == 1
    slide_card = section.slides[0]
    assert isinstance(slide_card, DraftSlideCard)
    assert slide_card.layout_hint == "Title"
    assert accumulator.ai_summary["used"] == 1
    assert len(accumulator.mapping_logs) == 1
    mapping_entry = accumulator.mapping_logs[0]
    assert mapping_entry["ai_recommendation_used"] is True
    assert mapping_entry["selected_usage_tags_detail"]["intro"]["label"] == "Introduction"


def test_process_work_item_updates_ai_invocation_summary() -> None:
    recommendation = RecommendationResult(
        candidates=[_make_candidate("Title", 0.5, 0.0)],
        ai_scores={},
        ai_response=LayoutAIResponse(
            model="gpt-test",
            recommended=[("Title", 0.5)],
            reasons={"Title": "best"},
            classifications={"Title": ("intro",)},
        ),
        classified_tags={"Title": ("intro",)},
        effective_tags={"Title": ("intro",)},
        baseline_tags={"Title": ("intro",)},
        ai_unknown_tags={},
    )
    recommender = _FakeRecommender(recommendation)
    accumulator = DraftAccumulator()
    options = DraftStructuringOptions()
    layout_profile = _base_layout_profile("Title")

    _process_work_item(
        options=options,
        item=DraftWorkItem(content_slide=_base_content_slide(), spec_slide=Slide(id="slide-1", layout="Title")),
        accumulator=accumulator,
        analyzer_map={},
        recommender=recommender,
        layout_lookup={"Title": layout_profile},
        tag_detail_map={},
        layouts=[layout_profile],
    )

    assert accumulator.ai_summary["invoked"] == 1
    assert accumulator.ai_summary["models"]["gpt-test"] == 1
    assert accumulator.ai_summary["used"] == 0


def test_process_work_item_tracks_ai_simulation_when_no_scores() -> None:
    recommendation = RecommendationResult(
        candidates=[_make_candidate("Title", 0.6, 0.4)],
        ai_scores={},
        ai_response=None,
        classified_tags={},
        effective_tags={},
        baseline_tags={},
        ai_unknown_tags={},
    )
    recommender = _FakeRecommender(recommendation)
    accumulator = DraftAccumulator()
    options = DraftStructuringOptions(enable_ai_recommender=True, enable_ai_simulation=True, ai_weight=0.25)
    layout_profile = _base_layout_profile("Title")

    _process_work_item(
        options=options,
        item=DraftWorkItem(content_slide=_base_content_slide(), spec_slide=None),
        accumulator=accumulator,
        analyzer_map={},
        recommender=recommender,
        layout_lookup={"Title": layout_profile},
        tag_detail_map={},
        layouts=[layout_profile],
    )

    assert accumulator.ai_summary["simulated"] == 1
    assert accumulator.ai_summary["used"] == 0
    assert accumulator.mapping_logs[0]["ai_recommendation_used"] is True


def test_resolve_section_prefers_story_angle_over_chapter_id() -> None:
    slide = SimpleNamespace(
        id="slide-1",
        intent="intent",
        story={"chapter_id": "chapter-1", "phase": "phase-one", "angle": "angle headline"},
    )
    key, name = _resolve_section(slide, None)
    assert key == "chapter-1"
    assert name == "angle headline"


def test_resolve_section_uses_phase_when_chapter_missing() -> None:
    slide = SimpleNamespace(
        id="slide-1",
        intent="intent",
        story={"phase": "problem"},
    )
    key, name = _resolve_section(slide, None)
    assert key == "problem"
    assert name == "Phase problem"


def test_resolve_section_falls_back_to_layout_hint() -> None:
    slide = SimpleNamespace(id="slide-1", intent=None)
    spec_slide = Slide(id="spec-1", layout="TitleSlide")
    key, name = _resolve_section(slide, spec_slide)
    assert key == "TitleSlide"
    assert name == "Layout: TitleSlide"


def test_resolve_section_final_fallback_uses_slide_id() -> None:
    slide = SimpleNamespace(id="slide-123", intent=None)
    key, name = _resolve_section(slide, None)
    assert key == "slide-123"
    assert name == "Slide: slide-123"
