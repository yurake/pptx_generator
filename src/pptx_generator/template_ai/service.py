"""テンプレート usage_tags 推定サービス。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..utils.usage_tags import CANONICAL_USAGE_TAGS, normalize_usage_tags_with_unknown
from .client import (
    TemplateAIClient,
    TemplateAIClientConfigurationError,
    TemplateAIRequest,
    TemplateAIResponse,
    create_template_ai_client,
)
from .policy import TemplateAIPolicy, TemplateAIPolicyError, TemplateAIPolicySet, load_template_policy_set

logger = logging.getLogger(__name__)
_TEMPLATE_LLM_LOGGER = logging.getLogger("pptx_generator.template_ai.llm")


@dataclass(slots=True)
class TemplateAIOptions:
    """テンプレート AI サービスの初期化オプション。"""

    policy_path: Path
    policy_id: str | None = None


@dataclass(slots=True)
class TemplateAIResult:
    """テンプレート AI 推定の結果。"""

    usage_tags: tuple[str, ...] | None
    unknown_tags: tuple[str, ...]
    reason: str | None
    raw_text: str | None
    source: str
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.usage_tags is not None and not self.error


class TemplateAIService:
    """テンプレート usage_tags を生成 AI で推定するサービス。"""

    def __init__(self, options: TemplateAIOptions) -> None:
        try:
            policy_set = load_template_policy_set(options.policy_path)
            self._policy = policy_set.get_policy(options.policy_id)
        except TemplateAIPolicyError as exc:
            raise TemplateAIPolicyError(str(exc)) from exc

        try:
            self._client: TemplateAIClient = create_template_ai_client(self._policy)
        except TemplateAIClientConfigurationError as exc:
            raise TemplateAIClientConfigurationError(str(exc)) from exc

    def classify_layout(
        self,
        *,
        template_id: str,
        layout_id: str,
        layout_name: str,
        placeholders: list[dict[str, Any]],
        text_hint: dict[str, Any],
        media_hint: dict[str, Any],
        heuristic_usage_tags: list[str],
    ) -> TemplateAIResult:
        """レイアウト単位で usage_tags を推定する。"""

        payload = {
            "template_id": template_id,
            "layout_id": layout_id,
            "layout_name": layout_name,
            "placeholders": placeholders,
            "text_hint": text_hint,
            "media_hint": media_hint,
            "heuristic_usage_tags": heuristic_usage_tags,
            "allowed_tags": sorted(CANONICAL_USAGE_TAGS),
        }

        if _TEMPLATE_LLM_LOGGER.isEnabledFor(logging.DEBUG):
            _TEMPLATE_LLM_LOGGER.debug(
                "template AI request payload: template=%s layout=%s heuristic=%s",
                template_id,
                layout_id,
                heuristic_usage_tags,
            )

        # 静的ルールがあれば先に適用する
        tags = self._apply_static_rules(layout_name)
        if tags is not None:
            canonical, unknown = normalize_usage_tags_with_unknown(tags)
            if _TEMPLATE_LLM_LOGGER.isEnabledFor(logging.DEBUG):
                _TEMPLATE_LLM_LOGGER.debug(
                    "template AI static rule matched: layout=%s tags=%s",
                    layout_id,
                    canonical,
                )
            return TemplateAIResult(
                usage_tags=canonical,
                unknown_tags=tuple(sorted(unknown)),
                reason="static-rule",
                raw_text=None,
                source="static",
            )

        prompt = self._policy.resolve_prompt()
        request = TemplateAIRequest(prompt=prompt, policy=self._policy, payload=payload)

        try:
            response = self._client.classify(request)
        except TemplateAIClientConfigurationError as exc:
            logger.warning("template AI classify failed: %s", exc)
            _TEMPLATE_LLM_LOGGER.warning(
                "template AI classify failed: layout=%s error=%s",
                layout_id,
                exc,
            )
            return TemplateAIResult(
                usage_tags=None,
                unknown_tags=(),
                reason=None,
                raw_text=None,
                source="error",
                error=str(exc),
            )

        usage_tags = response.usage_tags or ()
        canonical, unknown = normalize_usage_tags_with_unknown(usage_tags)

        if _TEMPLATE_LLM_LOGGER.isEnabledFor(logging.DEBUG):
            _TEMPLATE_LLM_LOGGER.debug(
                "template AI response summary: layout=%s source=%s tags=%s unknown=%s reason=%s",
                layout_id,
                response.model,
                canonical,
                unknown,
                response.reason,
            )
            if response.raw_text:
                _TEMPLATE_LLM_LOGGER.debug(
                    "template AI raw response (layout=%s): %s",
                    layout_id,
                    response.raw_text,
                )

        return TemplateAIResult(
            usage_tags=canonical if canonical else None,
            unknown_tags=tuple(sorted(unknown)),
            reason=response.reason,
            raw_text=response.raw_text,
            source=response.model,
        )

    def _apply_static_rules(self, layout_name: str) -> list[str] | None:
        for rule in self._policy.static_rules:
            if rule.matches(layout_name):
                return rule.tags
        return None
