"""Draft layout recommendation utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence, Tuple

from .draft_intel import clamp_score_detail, compute_analyzer_support
from .layout_ai import (
    LayoutAIPolicy,
    LayoutAIRequest,
    LayoutAIResponse,
    create_layout_ai_client,
    load_layout_policy_set,
)
from .layout_ai.client import LayoutAIClient, LayoutAIClientConfigurationError
from .layout_ai.policy import LayoutAIPolicyError, LayoutAIPolicySet
from .models import (
    ContentSlide,
    DraftAnalyzerSummary,
    DraftLayoutCandidate,
    DraftLayoutScoreDetail,
)
from .utils.usage_tags import (
    CANONICAL_USAGE_TAGS,
    normalize_usage_tag_value,
    normalize_usage_tags_with_unknown,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LayoutProfile:
    """layouts.jsonl の 1 レコードを抽象化したもの。"""

    layout_id: str
    layout_name: str
    usage_tags: tuple[str, ...]
    text_hint: dict[str, object]
    media_hint: dict[str, object]
    placeholder_summary: dict[str, object] = field(default_factory=dict)

    def allows_table(self) -> bool:
        return bool(self.media_hint.get("allow_table"))

    def max_lines(self) -> int | None:
        value = self.text_hint.get("max_lines")
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


@dataclass(slots=True)
class CardLayoutRecommenderConfig:
    """レイアウト推薦の設定。"""

    enable_ai: bool = True
    ai_weight: float = 0.25
    diversity_weight: float = 0.05
    max_candidates: int = 5
    policy_path: Path | None = None
    policy_id: str | None = None
    enable_simulated_ai: bool = True


@dataclass(slots=True)
class RecommendationResult:
    """レイアウト推薦の結果。"""

    candidates: list[tuple[DraftLayoutCandidate, DraftLayoutScoreDetail]]
    ai_scores: dict[str, float]
    ai_response: LayoutAIResponse | None
    classified_tags: dict[str, Tuple[str, ...]] = field(default_factory=dict)
    effective_tags: dict[str, Tuple[str, ...]] = field(default_factory=dict)
    baseline_tags: dict[str, Tuple[str, ...]] = field(default_factory=dict)
    ai_unknown_tags: dict[str, Tuple[str, ...]] = field(default_factory=dict)


class CardLayoutRecommender:
    """Brief カードとテンプレ情報からレイアウト候補を算出する。"""

    def __init__(self, config: CardLayoutRecommenderConfig | None = None) -> None:
        self._config = config or CardLayoutRecommenderConfig()
        self._policy_set: LayoutAIPolicySet | None = None
        self._policy: LayoutAIPolicy | None = None
        self._client: LayoutAIClient | None = None

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def recommend(
        self,
        *,
        slide: ContentSlide,
        preferred_layout: str,
        layouts: Sequence[LayoutProfile],
        analyzer_summary: DraftAnalyzerSummary | None = None,
    ) -> RecommendationResult:
        if not layouts:
            return RecommendationResult([], {}, None)

        slide_tags = self._extract_slide_tags(slide)
        (
            ai_scores,
            ai_response,
            ai_classified_tags,
            ai_unknown_tags,
        ) = self._apply_layout_ai(slide, layouts, analyzer_summary, slide_tags)

        baseline_tags = {
            profile.layout_id: tuple(profile.usage_tags) for profile in layouts
        }
        effective_tags: dict[str, tuple[str, ...]] = {}
        for layout_id, tags in baseline_tags.items():
            effective_tags[layout_id] = ai_classified_tags.get(layout_id, tags)

        evaluated: list[tuple[LayoutProfile, float, DraftLayoutScoreDetail]] = []

        for profile in layouts:
            override_tags = effective_tags.get(profile.layout_id, profile.usage_tags)
            score, detail = self._heuristic_score(
                profile,
                slide,
                slide_tags,
                analyzer_summary,
                override_tags,
            )
            evaluated.append((profile, score, detail))

        results: list[tuple[DraftLayoutCandidate, DraftLayoutScoreDetail]] = []

        for profile, score, detail in evaluated:
            layout_id = profile.layout_id
            override_tags = effective_tags.get(layout_id, profile.usage_tags)
            ai_value = ai_scores.get(layout_id)
            if ai_value is not None:
                detail.ai_recommendation = round(ai_value, 3)
                score += ai_value
            elif (
                self._config.enable_ai
                and self._config.enable_simulated_ai
                and self._config.ai_weight > 0
            ):
                simulated = self._simulate_ai_score(
                    profile,
                    slide,
                    preferred_layout,
                    slide_tags,
                    override_tags,
                )
                detail.ai_recommendation = round(simulated, 3)
                score += simulated

            detail = clamp_score_detail(detail)
            score = max(0.0, min(1.0, score))
            if score <= 0.0:
                continue

            candidate = DraftLayoutCandidate(layout_id=layout_id, score=round(score, 3))
            results.append((candidate, detail))

        results.sort(key=lambda item: item[0].score, reverse=True)
        return RecommendationResult(
            results[: self._config.max_candidates],
            ai_scores,
            ai_response,
            classified_tags=ai_classified_tags,
            effective_tags=effective_tags,
            baseline_tags=baseline_tags,
            ai_unknown_tags=ai_unknown_tags,
        )

    # ------------------------------------------------------------------ #
    # internal helpers
    # ------------------------------------------------------------------ #
    def _heuristic_score(
        self,
        profile: LayoutProfile,
        slide: ContentSlide,
        tags: set[str],
        analyzer_summary: DraftAnalyzerSummary | None,
        usage_tags_override: tuple[str, ...] | None = None,
    ) -> tuple[float, DraftLayoutScoreDetail]:
        score = 0.1
        detail = DraftLayoutScoreDetail(content_capacity=0.1)

        usage_tags_source = usage_tags_override or profile.usage_tags
        usage_tags = set(usage_tags_source)

        intent_tag = normalize_usage_tag_value(slide.intent)
        if intent_tag and intent_tag in usage_tags:
            score += 0.4
            detail.uses_tag += 0.4
        elif slide.intent and slide.intent.casefold() in usage_tags:
            score += 0.4
            detail.uses_tag += 0.4

        type_hint_tag = normalize_usage_tag_value(slide.type_hint)
        if type_hint_tag and type_hint_tag in usage_tags:
            score += 0.25
            detail.uses_tag += 0.25
        elif slide.type_hint and slide.type_hint.casefold() in usage_tags:
            score += 0.25
            detail.uses_tag += 0.25

        overlap = tags & usage_tags
        if overlap:
            bonus = min(0.15, 0.05 * len(overlap))
            score += bonus
            detail.uses_tag += round(bonus, 3)

        body_length = len(slide.elements.body)
        max_lines = profile.max_lines()
        if max_lines is not None:
            if body_length <= max_lines:
                score += 0.1
                detail.content_capacity += 0.1
            else:
                penalty = min(0.25, (body_length - max_lines) * 0.05)
                score -= penalty
                detail.content_capacity -= penalty

        has_table = slide.elements.table_data is not None
        if has_table and profile.allows_table():
            score += 0.1
            detail.content_capacity += 0.1
        elif has_table and not profile.allows_table():
            score -= 0.3
            detail.content_capacity -= 0.3

        if self._config.diversity_weight and usage_tags:
            diversity_bonus = min(self._config.diversity_weight, len(usage_tags) * 0.01)
            detail.diversity += round(diversity_bonus, 3)
            score += diversity_bonus

        analyzer_support = compute_analyzer_support(analyzer_summary)
        detail.analyzer_support = round(analyzer_support, 3)
        score += analyzer_support

        return score, detail

    def _apply_layout_ai(
        self,
        slide: ContentSlide,
        layouts: Sequence[LayoutProfile],
        analyzer_summary: DraftAnalyzerSummary | None,
        slide_tags: set[str],
    ) -> tuple[
        dict[str, float],
        LayoutAIResponse | None,
        dict[str, tuple[str, ...]],
        dict[str, tuple[str, ...]],
    ]:
        if not self._config.enable_ai or self._config.ai_weight <= 0:
            return {}, None, {}, {}

        bundle = self._ensure_layout_ai()
        if bundle is None:
            return {}, None, {}, {}
        policy, client = bundle

        candidate_ids = [profile.layout_id for profile in layouts]
        if not candidate_ids:
            return {}, None, {}, {}

        try:
            prompt = policy.resolve_prompt()
        except LayoutAIPolicyError as exc:
            logger.warning("layout AI prompt resolution failed: %s", exc)
            return {}, None, {}, {}

        card_payload = {
            "slide_id": slide.id,
            "intent": slide.intent,
            "type_hint": slide.type_hint,
            "title": slide.elements.title,
            "body": slide.elements.body,
            "note": slide.elements.note,
            "analyzer": analyzer_summary.model_dump(mode="json") if analyzer_summary else None,
            "allowed_tags": sorted(CANONICAL_USAGE_TAGS),
            "slide_tag_hints": sorted(tag for tag in slide_tags if tag),
        }

        layout_metadata = self._build_layout_metadata(layouts)

        request = LayoutAIRequest(
            prompt=prompt,
            policy=policy,
            card_payload=card_payload,
            layout_candidates=candidate_ids,
            layout_metadata=layout_metadata,
        )

        try:
            if logger.isEnabledFor(logging.INFO):
                logger.info(
                    "layout AI request: slide_id=%s candidates=%s",
                    slide.id,
                    candidate_ids,
                )
            response = client.recommend(request)
        except LayoutAIClientConfigurationError as exc:
            logger.info("layout AI recommend skipped: %s", exc)
            return {}, None, {}, {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("layout AI recommend failed: %s", exc)
            return {}, None, {}, {}

        scores: dict[str, float] = {}
        weight = max(0.0, min(1.0, self._config.ai_weight))
        for layout_id, raw_score in response.recommended:
            if layout_id not in candidate_ids:
                continue
            normalized = max(0.0, min(1.0, float(raw_score))) * weight
            if normalized <= 0.0:
                continue
            scores[layout_id] = round(normalized, 3)

        ai_classified: dict[str, tuple[str, ...]] = {}
        ai_unknown: dict[str, tuple[str, ...]] = {}
        classifications = getattr(response, "classifications", {}) or {}
        for layout_id, raw_tags in classifications.items():
            if not raw_tags:
                continue
            normalized, unknown = normalize_usage_tags_with_unknown(raw_tags)
            if normalized:
                ai_classified[layout_id] = normalized
            if unknown:
                ai_unknown[layout_id] = tuple(sorted(unknown))

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "layout AI response summary: slide_id=%s model=%s used_layouts=%s classifications=%s",
                slide.id,
                response.model,
                list(scores.keys()),
                ai_classified,
            )
        return scores, response, ai_classified, ai_unknown

    @staticmethod
    def _build_layout_metadata(
        layouts: Sequence[LayoutProfile],
    ) -> dict[str, dict[str, object]]:
        metadata: dict[str, dict[str, object]] = {}
        for profile in layouts:
            entry: dict[str, object] = {
                "layout_name": profile.layout_name,
                "usage_tags_rule": list(profile.usage_tags),
                "text_hint": profile.text_hint,
                "media_hint": profile.media_hint,
            }
            if profile.placeholder_summary:
                summary = profile.placeholder_summary
                counts = summary.get("counts")
                if counts:
                    entry["placeholder_counts"] = counts
                details = summary.get("details")
                if details:
                    entry["placeholders"] = details
                extras = summary.get("attributes")
                if extras:
                    entry["placeholder_attributes"] = extras
            metadata[profile.layout_id] = entry
        return metadata

    def _ensure_layout_ai(self) -> tuple[LayoutAIPolicy, LayoutAIClient] | None:
        path = self._config.policy_path
        if path is None:
            return None
        if self._policy is not None and self._client is not None:
            return self._policy, self._client
        try:
            policy_set = load_layout_policy_set(Path(path))
            policy = policy_set.get_policy(self._config.policy_id)
            client = create_layout_ai_client(policy)
        except LayoutAIPolicyError as exc:
            logger.warning("layout AI policy error: %s", exc)
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("layout AI client initialization failed: %s", exc)
            return None
        self._policy_set = policy_set
        self._policy = policy
        self._client = client
        return policy, client

    def _simulate_ai_score(
        self,
        profile: LayoutProfile,
        slide: ContentSlide,
        preferred_layout: str,
        tags: set[str],
        usage_tags_override: tuple[str, ...] | None = None,
    ) -> float:
        """LLM連携前提のスコアを簡易シミュレーションする。"""
        boost = 0.0

        if profile.layout_id == preferred_layout:
            boost += self._config.ai_weight * 0.6

        if slide.ai_review and slide.ai_review.grade == "A":
            boost += self._config.ai_weight * 0.2
        elif slide.ai_review and slide.ai_review.grade == "B":
            boost += self._config.ai_weight * 0.1

        usage_tags_source = usage_tags_override or profile.usage_tags
        usage_tags = set(usage_tags_source)
        if tags and usage_tags:
            overlap = tags & usage_tags
            if overlap:
                boost += min(self._config.ai_weight * 0.3, 0.05 * len(overlap))

        return min(self._config.ai_weight, boost)

    @staticmethod
    def _extract_slide_tags(slide: ContentSlide) -> set[str]:
        tags: set[str] = set()
        if slide.intent:
            canonical_intent = normalize_usage_tag_value(slide.intent)
            tags.add(canonical_intent or slide.intent.casefold())
        if slide.type_hint:
            canonical_hint = normalize_usage_tag_value(slide.type_hint)
            tags.add(canonical_hint or slide.type_hint.casefold())

        title = slide.elements.title.lower()
        for token in CardLayoutRecommender._tokenize(title):
            if len(token) >= 3:
                canonical_token = normalize_usage_tag_value(token)
                tags.add(canonical_token or token)

        for line in slide.elements.body:
            for token in CardLayoutRecommender._tokenize(line.lower()):
                if len(token) >= 3:
                    canonical_token = normalize_usage_tag_value(token)
                    tags.add(canonical_token or token)
        return tags

    @staticmethod
    def _tokenize(text: str) -> Iterable[str]:
        separators = " ,;:./\n\t"
        token = []
        for ch in text:
            if ch in separators:
                if token:
                    yield "".join(token)
                    token = []
                continue
            token.append(ch)
        if token:
            yield "".join(token)
