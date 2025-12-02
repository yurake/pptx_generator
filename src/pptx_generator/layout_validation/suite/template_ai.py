"""テンプレートAI関連のロジックを集約するモジュール。"""

from __future__ import annotations

import logging
from importlib import import_module
from time import perf_counter
from typing import Any, Iterable, Sequence, Type

from ...models import LayoutInfo
from ...template_ai import TemplateAIOptions, TemplateAIResult, TemplateAIService as BaseTemplateAIService
from ...template_ai.client import TemplateAIClientConfigurationError
from ...template_ai.policy import TemplateAIPolicyError
from ...utils.layout_metadata import HeuristicUsageTagsResult
from ...utils.usage_tags import normalize_usage_tags_with_unknown
from .types import LayoutValidationOptions

logger = logging.getLogger(__name__)

# backward-compatible alias exposed via package __all__
TemplateAIService = BaseTemplateAIService


class TemplateAIManager:
    """テンプレートAIの初期化と呼び出しを担当する。"""

    def __init__(self, options: LayoutValidationOptions) -> None:
        self._options = options
        self._service: TemplateAIService | None = None
        self._stats: dict[str, int] = {}
        self._layouts: list[dict[str, Any]] = []
        self._initialize_template_ai()
        self.reset_run()

    # ------------------------------------------------------------------ #
    # ライフサイクル
    # ------------------------------------------------------------------ #
    def reset_run(self) -> None:
        self._stats = {
            "invoked": 0,
            "success": 0,
            "fallback": 0,
            "failed": 0,
        }
        self._layouts = []

    def _initialize_template_ai(self) -> None:
        if self._options.disable_template_ai:
            logger.info("template AI is disabled by option")
            return
        policy_path = self._options.template_ai_policy_path
        if policy_path is None:
            return
        try:
            service_cls = _resolve_template_ai_service()
            service = service_cls(
                TemplateAIOptions(
                    policy_path=policy_path,
                    policy_id=self._options.template_ai_policy_id,
                )
            )
        except (TemplateAIPolicyError, TemplateAIClientConfigurationError) as exc:
            logger.warning("テンプレートAIの初期化に失敗しました: %s", exc)
            return
        self._service = service

    # ------------------------------------------------------------------ #
    # 呼び出し
    # ------------------------------------------------------------------ #
    def apply(
        self,
        *,
        template_id: str,
        layout_id: str,
        layout: LayoutInfo,
        placeholder_records: Sequence[dict[str, Any]],
        text_hint: dict[str, Any],
        media_hint: dict[str, Any],
        heuristic_tags: Iterable[str],
        placeholder_summary: dict[str, Any],
        blueprint_info: dict[str, Any] | None,
        meta_payload: dict[str, Any],
    ) -> tuple[set[str], TemplateAIResult | None, bool, list[dict[str, Any]], list[dict[str, Any]]]:
        raw_usage_tags = set(heuristic_tags)
        warnings: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        ai_error = False

        ai_result = self._invoke_template_ai(
            template_id=template_id,
            layout_id=layout_id,
            layout_name=layout.name or layout_id,
            placeholders=list(placeholder_records),
            text_hint=text_hint,
            media_hint=media_hint,
            heuristic_usage_tags=sorted(heuristic_tags),
            placeholder_summary=placeholder_summary,
            blueprint=blueprint_info,
            meta=meta_payload or None,
        )

        if ai_result and ai_result.success and ai_result.usage_tags:
            raw_usage_tags = set(ai_result.usage_tags)
            if ai_result.source == "static":
                raw_usage_tags.update(heuristic_tags)
        elif ai_result:
            if ai_result.error:
                ai_error = True
                raw_usage_tags = set()
                errors.append(
                    {
                        "code": "usage_tag_ai_error",
                        "layout_id": layout_id,
                        "name": layout.name,
                        "detail": ai_result.error,
                    }
                )
            elif ai_result.source != "static":
                warnings.append(
                    {
                        "code": "usage_tag_ai_fallback",
                        "layout_id": layout_id,
                        "name": layout.name,
                        "detail": "生成AIが使用できなかったためヒューリスティックへフォールバックしました",
                    }
                )

        return raw_usage_tags, ai_result, ai_error, warnings, errors

    def normalize_usage_tags(
        self,
        *,
        layout_id: str,
        layout_name: str | None,
        raw_usage_tags: set[str],
        heuristic_result: HeuristicUsageTagsResult,
        ai_result: TemplateAIResult | None,
        ai_error: bool,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        usage_tags_tuple, unknown_tags = normalize_usage_tags_with_unknown(raw_usage_tags)
        usage_tags_set = set(usage_tags_tuple)

        if "title" in usage_tags_set and heuristic_result.has_body_placeholder and not heuristic_result.title_from_name:
            usage_tags_set.discard("title")

        if ai_error:
            usage_tags = sorted(usage_tags_set)
        else:
            if not usage_tags_set:
                usage_tags_set.add("generic")
            usage_tags = sorted(usage_tags_set)

        warnings: list[dict[str, Any]] = []
        if ai_result and ai_result.success:
            if ai_result.unknown_tags:
                warnings.append(
                    {
                        "code": "usage_tag_ai_unknown",
                        "layout_id": layout_id,
                        "name": layout_name,
                        "detail": ", ".join(ai_result.unknown_tags),
                    }
                )
        elif unknown_tags:
            warnings.append(
                {
                    "code": "usage_tag_unknown",
                    "layout_id": layout_id,
                    "name": layout_name,
                    "detail": ", ".join(sorted(unknown_tags)),
                }
            )

        return usage_tags, warnings

    # ------------------------------------------------------------------ #
    # 情報取得
    # ------------------------------------------------------------------ #
    def build_meta_payload(
        self,
        *,
        layout: LayoutInfo,
        base_meta_reasons: Sequence[str],
    ) -> dict[str, Any]:
        meta: dict[str, Any] = {}
        if base_meta_reasons:
            meta["heuristic_reason"] = "; ".join(base_meta_reasons)
        if layout.layout_description:
            meta["layout_description"] = layout.layout_description
        return meta

    def policy_static_rules(self) -> list[dict[str, Any]]:
        service = self._service
        if service is None:
            return []
        policy = getattr(service, "_policy", None)
        if policy is None:
            return []
        payload: list[dict[str, Any]] = []
        for rule in policy.static_rules:
            payload.append(
                {
                    "layout_name_pattern": rule.layout_name_pattern,
                    "tags": list(rule.tags),
                }
            )
        return payload


    def stats(self) -> dict[str, int]:
        return dict(self._stats)

    def layouts(self) -> list[dict[str, Any]]:
        return list(self._layouts)

    # ------------------------------------------------------------------ #
    # 内部ヘルパー
    # ------------------------------------------------------------------ #
    def _invoke_template_ai(
        self,
        *,
        template_id: str,
        layout_id: str,
        layout_name: str,
        placeholders: list[dict[str, Any]],
        text_hint: dict[str, Any],
        media_hint: dict[str, Any],
        heuristic_usage_tags: list[str],
        placeholder_summary: dict[str, Any],
        blueprint: dict[str, Any] | None,
        meta: dict[str, Any] | None,
    ) -> TemplateAIResult | None:
        service = self._service
        if service is None:
            return None

        self._stats = {
            key: self._stats.get(key, 0)
            for key in ("invoked", "success", "fallback", "failed")
        }
        self._stats["invoked"] += 1
        started = perf_counter()
        result: TemplateAIResult | None = None
        try:
            result = service.classify_layout(
                template_id=template_id,
                layout_id=layout_id,
                layout_name=layout_name,
                placeholders=placeholders,
                text_hint=text_hint,
                media_hint=media_hint,
                heuristic_usage_tags=heuristic_usage_tags,
                placeholder_summary=placeholder_summary,
                blueprint=blueprint,
                meta=meta,
            )
        except TemplateAIClientConfigurationError as exc:
            logger.warning("template AI classify failed: %s", exc)
            self._stats["failed"] += 1
            self._layouts.append(
                {
                    "layout_id": layout_id,
                    "layout_name": layout_name,
                    "source": "error",
                    "reason": None,
                    "tags": [],
                    "unknown_tags": [],
                    "error": str(exc),
                }
            )
            return None
        finally:
            elapsed = perf_counter() - started
            if logger.isEnabledFor(logging.DEBUG) or elapsed > 0.5:
                source = getattr(result, "source", "-") if result else "-"
                logger.info(
                    "template AI classify: layout=%s provider=%s elapsed=%.3fs",
                    layout_id,
                    source,
                    elapsed,
                )

        if result is None:
            return None

        if result.success:
            self._stats["success"] += 1
        elif result.source == "static":
            self._stats["fallback"] += 1
        else:
            self._stats["failed"] += 1

        self._layouts.append(
            {
                "layout_id": layout_id,
                "layout_name": layout_name,
                "source": result.source,
                "reason": result.reason,
                "tags": list(result.usage_tags or ()),
                "unknown_tags": list(result.unknown_tags),
                "error": result.error,
            }
        )

        return result


def _resolve_template_ai_service() -> Type[BaseTemplateAIService]:
    suite_module = import_module("pptx_generator.layout_validation.suite")
    service_cls = getattr(suite_module, "TemplateAIService", None)
    if service_cls is None:
        return BaseTemplateAIService
    return service_cls
