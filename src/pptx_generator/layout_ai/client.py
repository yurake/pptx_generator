"""レイアウト推薦 AI クライアント。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
import re
from typing import Callable, Iterable, Protocol, Tuple
import time

from pptx_generator.llm import (
    log_provider_resolution,
    resolve_llm_provider,
    load_anthropic_config,
    load_azure_openai_config,
    load_aws_claude_config,
    load_openai_chat_config,
)
from ..llm.json_utils import extract_json_object as parse_json_object

from .policy import LayoutAIPolicy, LayoutAIPolicyError
from .prompts import build_system_prompt, build_user_prompt

logger = logging.getLogger(__name__)

_LAYOUT_LLM_LOGGER = logging.getLogger("pptx_generator.layout_ai.llm")
DEFAULT_MAX_TOKENS = 32000


@dataclass(slots=True)
class LayoutAIRequest:
    """レイアウト推薦 AI へのリクエスト。"""

    prompt: str
    policy: LayoutAIPolicy
    card_payload: dict[str, object]
    layout_candidates: list[str]
    layout_metadata: dict[str, dict[str, object]] = field(default_factory=dict)


@dataclass(slots=True)
class LayoutAIResponse:
    """レイアウト推薦 AI からの応答。"""

    model: str
    recommended: list[tuple[str, float]] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)
    classifications: dict[str, Tuple[str, ...]] = field(default_factory=dict)
    raw_text: str | None = None


class LayoutAIClient(Protocol):
    """レイアウト推薦 AI クライアントのインターフェース。"""

    def recommend(self, request: LayoutAIRequest) -> LayoutAIResponse:
        """カード情報からレイアウト候補を評価する。"""


class LayoutAIClientConfigurationError(RuntimeError):
    """クライアント設定のエラー。"""


class LayoutAIClientExecutionError(RuntimeError):
    """LLM 呼び出し時の実行エラー。"""


class LayoutAIResponseFormatError(RuntimeError):
    """LLM 応答の解析に失敗した場合の例外。"""


def create_layout_ai_client(policy: LayoutAIPolicy) -> LayoutAIClient:
    resolution = resolve_llm_provider()
    log_provider_resolution(
        logger,
        component="layout_ai",
        resolution=resolution,
        policy_id=getattr(policy, "id", "-"),
    )

    factories: dict[str, Callable[[], LayoutAIClient]] = {
        "mock": MockLayoutAIClient,
        "openai": OpenAIChatLayoutClient.from_env,
        "azure-openai": AzureOpenAIChatLayoutClient.from_env,
        "anthropic": AnthropicClaudeLayoutClient.from_env,
        "aws-claude": AwsClaudeLayoutClient.from_env,
    }

    factory = factories.get(resolution.provider)
    if factory is None:
        raise LayoutAIClientConfigurationError(
            f"未知のレイアウトAIプロバイダが指定されました: {resolution.provider}"
        )

    return factory()


class MockLayoutAIClient:
    """決定論的なモック。"""

    def recommend(self, request: LayoutAIRequest) -> LayoutAIResponse:
        weights: list[tuple[str, float]] = []
        for index, layout_id in enumerate(request.layout_candidates):
            base = 0.6 if index == 0 else 0.4
            bonus = 0.1 * (index + 1) / max(len(request.layout_candidates), 1)
            score = min(1.0, round(base + bonus, 3))
            weights.append((layout_id, score))
        reasons = {layout: "mock-recommended" for layout, _ in weights}
        classifications: dict[str, Tuple[str, ...]] = {}
        metadata = request.layout_metadata or {}
        for layout_id in request.layout_candidates:
            entry = metadata.get(layout_id, {})
            tags = entry.get("usage_tags_rule") or entry.get("usage_tags")
            if isinstance(tags, (list, tuple)):
                canonical = tuple(str(tag) for tag in tags if str(tag))
                if canonical:
                    classifications[layout_id] = canonical
        payload = {
            "model": "mock-layout",
            "recommended": [{"layout_id": layout, "score": score} for layout, score in weights],
            "reasons": reasons,
            "classifications": {key: list(value) for key, value in classifications.items()},
        }
        raw_text = json.dumps(payload, ensure_ascii=False)
        return LayoutAIResponse(
            model="mock-layout",
            recommended=weights,
            reasons=reasons,
            classifications=classifications,
            raw_text=raw_text,
        )


class OpenAIChatLayoutClient:
    """OpenAI Chat completions を利用したレイアウト推薦。"""

    def __init__(self, client, *, model: str, temperature: float, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    @classmethod
    def from_env(cls) -> "OpenAIChatLayoutClient":
        from openai import OpenAI

        config = load_openai_chat_config(
            default_model="gpt-5-mini",
            default_temperature=0.0,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            error_cls=LayoutAIClientConfigurationError,
        )
        client = OpenAI(api_key=config.api_key, base_url=config.base_url) if config.base_url else OpenAI(api_key=config.api_key)
        return cls(client, model=config.model, temperature=config.temperature, max_tokens=config.max_tokens)

    def recommend(self, request: LayoutAIRequest) -> LayoutAIResponse:
        from openai.types.responses import ResponseOutputMessage, ResponseOutputRefusal, ResponseOutputText

        start = time.perf_counter()
        _LAYOUT_LLM_LOGGER.info(
            "layout AI call start: model=%s layout_candidates=%s",
            self._model,
            request.layout_candidates,
        )
        messages = [
            {"role": "system", "content": build_system_prompt(request)},
            {"role": "user", "content": build_user_prompt(request)},
        ]
        kwargs: dict[str, object] = {
            "input": messages,
            "temperature": self._temperature,
            "response_format": {"type": "json_object"},
        }
        if self._max_tokens > 0:
            kwargs["max_output_tokens"] = self._max_tokens

        try:
            response = self._client.responses.create(  # type: ignore[attr-defined]
                model=self._model,
                **kwargs,
            )
        except Exception as exc:
            logger.error(
                "OpenAI layout request failed: model=%s candidates=%s error=%s",
                self._model,
                request.layout_candidates,
                exc,
            )
            raise LayoutAIClientExecutionError(str(exc)) from exc

        latency_ms = (time.perf_counter() - start) * 1000
        logger.debug("OpenAI layout raw response: %s", response)
        text_segments: list[str] = []
        incomplete = False
        for item in getattr(response, "output", []) or []:
            if isinstance(item, ResponseOutputMessage):
                if getattr(item, "status", None) == "incomplete":
                    incomplete = True
                for content in item.content:
                    if isinstance(content, ResponseOutputText):
                        text_segments.append(content.text)
                    elif isinstance(content, ResponseOutputRefusal):  # pragma: no cover - refusal path
                        logger.info("OpenAI layout AI refusal: %s", content.refusal)
        if getattr(response, "status", None) == "incomplete":
            incomplete = True
        if incomplete:
            logger.error(
                "OpenAI layout model %s returned incomplete response",
                getattr(response, "model", self._model),
            )
            raise LayoutAIResponseFormatError("OpenAI layout AI から不完全な応答が返されました")

        content = "\n".join(segment.strip() for segment in text_segments if segment and segment.strip())
        if not content:
            logger.error(
                "OpenAI layout model %s returned empty content",
                getattr(response, "model", self._model),
            )
            raise LayoutAIResponseFormatError("OpenAI layout AI の応答が空でした")

        raw = content
        truncated = False
        if len(raw) > 2000:
            raw = raw[:2000]
            truncated = True

        _LAYOUT_LLM_LOGGER.info(
            "layout AI call done: model=%s prompt_len=%s response_len=%s truncated=%s latency_ms=%.1f prompt=%s response=%s",
            getattr(response, "model", self._model),
            len(request.prompt),
            len(content),
            truncated,
            latency_ms,
            request.prompt,
            raw,
        )

        try:
            parsed = _parse_layout_response(content, model=getattr(response, "model", self._model))
        except LayoutAIResponseFormatError as exc:
            logger.error(
                "OpenAI layout model %s response parsing failed: %s",
                getattr(response, "model", self._model),
                exc,
            )
            raise

        if not parsed.recommended:
            logger.error(
                "OpenAI layout model %s returned no recommendations",
                parsed.model,
            )
            raise LayoutAIResponseFormatError("OpenAI layout AI からレイアウト候補が返却されませんでした")

        return parsed


class AzureOpenAIChatLayoutClient:
    """Azure OpenAI Chat Completions API を利用したレイアウト推薦。"""

    def __init__(self, client, *, deployment: str, temperature: float, max_tokens: int) -> None:
        self._client = client
        self._deployment = deployment
        self._temperature = temperature
        self._max_tokens = max_tokens

    @classmethod
    def from_env(cls) -> "AzureOpenAIChatLayoutClient":
        from openai import AzureOpenAI

        config = load_azure_openai_config(
            default_temperature=0.0,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            default_api_version="2024-02-15-preview",
            error_cls=LayoutAIClientConfigurationError,
        )
        client = AzureOpenAI(
            api_key=config.api_key,
            azure_endpoint=config.endpoint,
            api_version=config.api_version,
        )
        return cls(client, deployment=config.deployment, temperature=config.temperature, max_tokens=config.max_tokens)

    def recommend(self, request: LayoutAIRequest) -> LayoutAIResponse:
        from openai.types.responses import ResponseOutputMessage
        from openai.types.responses.response_output_text import ResponseOutputText
        from openai.types.responses.response_output_refusal import ResponseOutputRefusal

        messages = [
            {"role": "system", "content": build_system_prompt(request)},
            {"role": "user", "content": build_user_prompt(request)},
        ]
        request_model = self._deployment
        kwargs: dict[str, object] = {
            "model": request_model,
            "input": messages,
            "temperature": self._temperature,
        }
        kwargs["response_format"] = {"type": "json_object"}
        if self._max_tokens > 0:
            kwargs["max_output_tokens"] = self._max_tokens

        attempt_kwargs = dict(kwargs)
        for attempt in range(2):
            try:
                response = self._client.responses.create(**attempt_kwargs)  # type: ignore[attr-defined]
                break
            except TypeError as exc:
                message = str(exc)
                if "response_format" in message and "unexpected" in message.lower():
                    attempt_kwargs.pop("response_format", None)
                    continue
                raise
        else:  # pragma: no cover - safeguard
            raise LayoutAIClientConfigurationError("Azure OpenAI 応答を取得できませんでした")
        logger.debug("Azure OpenAI raw response: %s", response)
        text_segments: list[str] = []
        for item in getattr(response, "output", []) or []:
            if isinstance(item, ResponseOutputMessage):
                for content in item.content:
                    if isinstance(content, ResponseOutputText):
                        text_segments.append(content.text)
                    elif isinstance(content, ResponseOutputRefusal):  # pragma: no cover - refusal path
                        logger.info("Azure OpenAI layout AI refusal: %s", content.refusal)
        content = "\n".join(segment.strip() for segment in text_segments if segment.strip())
        if not content:
            raise LayoutAIClientConfigurationError("Azure OpenAI 応答が空でした")
        try:
            return _parse_layout_response(content, model=request_model)
        except LayoutAIResponseFormatError as exc:
            logger.debug("Azure OpenAI layout response parse failed: %s", exc)
            return LayoutAIResponse(model=request_model, raw_text=content)


class AnthropicClaudeLayoutClient:
    """Anthropic Claude API を利用したレイアウト推薦。"""

    def __init__(self, client, *, model: str, max_tokens: int, temperature: float) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature

    @classmethod
    def from_env(cls) -> "AnthropicClaudeLayoutClient":
        import anthropic

        config = load_anthropic_config(
            default_model="claude-3-haiku-20240307",
            default_temperature=0.0,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            error_cls=LayoutAIClientConfigurationError,
        )
        client = anthropic.Anthropic(api_key=config.api_key)
        return cls(client, model=config.model, max_tokens=config.max_tokens, temperature=config.temperature)

    def recommend(self, request: LayoutAIRequest) -> LayoutAIResponse:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": build_user_prompt(request),
                    }
                ],
            }
        ]
        try:
            response = self._client.messages.create(  # type: ignore[attr-defined]
                model=self._model,
                system=build_system_prompt(request),
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                messages=messages,
            )
        except Exception as exc:  # pragma: no cover - API failure
            logger.error(
                "Anthropic layout request failed: model=%s candidates=%s error=%s",
                self._model,
                request.layout_candidates,
                exc,
            )
            raise LayoutAIClientExecutionError(str(exc)) from exc

        text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        content = "\n".join(part.strip() for part in text_parts if part and part.strip())
        if not content:
            logger.error("Anthropic layout model %s returned empty content", getattr(response, "model", self._model))
            raise LayoutAIResponseFormatError("Anthropic 応答が空でした")
        try:
            parsed = _parse_layout_response(content, model=getattr(response, "model", self._model))
        except LayoutAIResponseFormatError as exc:
            logger.error("Anthropic layout response parse failed: %s", exc)
            raise

        if not parsed.recommended:
            logger.error("Anthropic layout model %s returned no recommendations", parsed.model)
            raise LayoutAIResponseFormatError("Anthropic レイアウトAIから候補が返されませんでした")

        return parsed


class AwsClaudeLayoutClient:
    """AWS Bedrock Claude を利用したレイアウト推薦。"""

    def __init__(
        self,
        runtime_client,
        *,
        model_id: str,
        max_tokens: int,
        inference_profile_arn: str | None,
        temperature: float,
    ) -> None:
        self._client = runtime_client
        self._model_id = model_id
        self._max_tokens = max_tokens
        self._inference_profile_arn = inference_profile_arn
        self._temperature = temperature

    @classmethod
    def from_env(cls) -> "AwsClaudeLayoutClient":
        import boto3
        from botocore.exceptions import NoCredentialsError

        config = load_aws_claude_config(
            default_model_id="anthropic.claude-3-haiku-20240307-v1:0",
            default_temperature=0.0,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            error_cls=LayoutAIClientConfigurationError,
        )

        session_kwargs: dict[str, object] = {}
        if config.profile:
            session_kwargs["profile_name"] = config.profile
        if config.region:
            session_kwargs["region_name"] = config.region
        session = boto3.Session(**session_kwargs)
        credentials = session.get_credentials()
        if credentials is None:
            raise LayoutAIClientConfigurationError(
                "AWS 認証情報が見つかりません。環境変数や共有クレデンシャルで設定してください。"
            )

        client_kwargs: dict[str, object] = {}
        if config.region:
            client_kwargs["region_name"] = config.region
        try:
            runtime_client = session.client("bedrock-runtime", **client_kwargs)
        except NoCredentialsError as exc:
            raise LayoutAIClientConfigurationError(
                "AWS 認証情報を利用できません。AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY を設定してください。"
            ) from exc

        return cls(
            runtime_client,
            model_id=config.model_id,
            max_tokens=config.max_tokens,
            inference_profile_arn=config.inference_profile_arn,
            temperature=config.temperature,
        )

    def recommend(self, request: LayoutAIRequest) -> LayoutAIResponse:
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "system": build_system_prompt(request),
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": build_user_prompt(request),
                        }
                    ],
                }
            ],
        }
        model_id = self._model_id
        invoke_kwargs: dict[str, object] = {
            "modelId": model_id,
            "body": json.dumps(payload),
            "contentType": "application/json",
            "accept": "application/json",
        }
        if self._inference_profile_arn:
            invoke_kwargs["inferenceProfileArn"] = self._inference_profile_arn

        response = self._client.invoke_model(**invoke_kwargs)
        body = response.get("body")
        body_text = body.read() if hasattr(body, "read") else body
        data = json.loads(body_text)
        text_parts = [item.get("text", "") for item in data.get("content", []) if isinstance(item, dict)]
        content = "\n".join(text_parts)
        if not content:
            raise LayoutAIClientConfigurationError("AWS Claude 応答が空でした")
        try:
            return _parse_layout_response(content, model=model_id)
        except LayoutAIResponseFormatError as exc:
            logger.debug("AWS Claude layout response parse failed: %s", exc)
            return LayoutAIResponse(model=model_id, raw_text=content)


def _parse_layout_response(text: str, *, model: str) -> LayoutAIResponse:
    try:
        data = _extract_json_object(text)
    except json.JSONDecodeError as exc:
        raise LayoutAIResponseFormatError(text) from exc

    recommended_map: dict[str, float] = {}
    reasons_map: dict[str, str] = {}
    classifications_map: dict[str, Tuple[str, ...]] = {}
    order: list[str] = []

    def register(
        layout_id: str,
        score: float | None,
        reason: object | None,
        tags: Iterable[str] | None,
    ) -> None:
        if layout_id not in order:
            order.append(layout_id)
        if score is not None:
            try:
                value = float(score)
                recommended_map[layout_id] = max(0.0, min(1.0, value))
            except (TypeError, ValueError):
                pass
        if layout_id not in reasons_map and reason is not None:
            reasons_map[layout_id] = _stringify_reason(reason)
        if layout_id not in classifications_map:
            tag_candidates: list[str] = []
            if tags:
                tag_candidates.extend(tags)
            tag_candidates.extend(_extract_tags_from_reason(reason))
            deduped = _deduplicate_tags(tag_candidates)
            if deduped:
                classifications_map[layout_id] = deduped

    for layout_id, score, reason, tags in _iter_layout_candidates(data):
        if not layout_id:
            continue
        register(layout_id, score, reason, tags)

    fallback_choice = data.get("recommended_layout") or data.get("best_layout")
    if isinstance(fallback_choice, str):
        register(fallback_choice, recommended_map.get(fallback_choice, 1.0), None, None)

    direct_reasons = data.get("reasons")
    if isinstance(direct_reasons, dict):
        for key, value in direct_reasons.items():
            reasons_map[str(key)] = _stringify_reason(value)
            if str(key) not in classifications_map:
                deduped = _deduplicate_tags(_coerce_tag_candidates(value))
                if deduped:
                    classifications_map[str(key)] = deduped

    direct_classifications = data.get("classifications")
    if isinstance(direct_classifications, dict):
        for key, value in direct_classifications.items():
            deduped = _deduplicate_tags(_coerce_tag_candidates(value))
            if deduped:
                classifications_map[str(key)] = deduped

    entries: list[tuple[str, float]] = []
    for layout_id in order:
        score = recommended_map.get(layout_id, 0.0)
        entries.append((layout_id, score))

    return LayoutAIResponse(
        model=model,
        recommended=entries,
        reasons=reasons_map,
        classifications=classifications_map,
        raw_text=text,
    )


def _extract_json_object(text: str) -> dict[str, object]:
    return parse_json_object(text)


def _iter_layout_candidates(
    data: dict[str, object],
) -> Iterable[tuple[str | None, float | None, object | None, list[str]]]:
    buckets: list[object] = []
    for key in (
        "recommended",
        "recommendations",
        "layout_rankings",
        "evaluation_results",
        "candidates",
        "results",
    ):
        value = data.get(key)
        if isinstance(value, list):
            buckets.append(value)

    for bucket in buckets:
        for item in bucket:  # type: ignore[assignment]
            if not isinstance(item, dict):
                continue
            layout_id = _coerce_layout_id(item)
            score = _coerce_layout_score(item)
            reason = _extract_reason(item)
            tags = _extract_tags_from_item(item)
            yield layout_id, score, reason, tags


def _coerce_layout_id(item: dict[str, object]) -> str | None:
    for key in (
        "layout_id",
        "layoutId",
        "layout_name",
        "layout",
        "layout_provider",
        "id",
    ):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _coerce_layout_score(item: dict[str, object]) -> float | None:
    for key in (
        "score",
        "fit_score",
        "match_score",
        "confidence",
        "probability",
        "weight",
        "ranking_score",
    ):
        value = item.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _extract_reason(item: dict[str, object]) -> object | None:
    for key in ("reason", "reasons", "reasoning", "explanation", "notes"):
        if key in item:
            return item[key]
    return None


def _extract_tags_from_item(item: dict[str, object]) -> list[str]:
    for key in ("tags", "usage_tags", "classification", "classifications"):
        if key in item:
            tags = _coerce_tag_candidates(item[key])
            if tags:
                return tags
    return []


def _coerce_tag_candidates(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [part.strip() for part in re.split(r"[,\s/]+", value) if part.strip()]
        return parts
    if isinstance(value, dict):
        collected: list[str] = []
        for key in ("tags", "usage_tags", "tag", "label", "name", "classification"):
            if key in value:
                collected.extend(_coerce_tag_candidates(value[key]))
        return collected
    if isinstance(value, (list, tuple, set)):
        collected: list[str] = []
        for item in value:
            collected.extend(_coerce_tag_candidates(item))
        return collected
    return []


def _deduplicate_tags(tags: Iterable[str]) -> Tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for tag in tags:
        normalized = str(tag).strip().casefold()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return tuple(ordered)


def _extract_tags_from_reason(reason: object) -> list[str]:
    if reason is None:
        return []
    return _coerce_tag_candidates(reason)


def _stringify_reason(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        parts = [f"{k}: {v}" for k, v in value.items()]
        return "; ".join(str(part) for part in parts if part)
    if isinstance(value, (list, tuple)):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return " / ".join(parts)
    return str(value)
