"""レイアウト推薦 AI クライアント。"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
import re
from typing import Iterable, Protocol, Tuple

from .policy import LayoutAIPolicy, LayoutAIPolicyError

logger = logging.getLogger(__name__)

_LAYOUT_LLM_LOGGER = logging.getLogger("pptx_generator.layout_ai.llm")
DEFAULT_MAX_TOKENS = 512


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


class LayoutAIResponseFormatError(RuntimeError):
    """LLM 応答の解析に失敗した場合の例外。"""


def create_layout_ai_client(policy: LayoutAIPolicy) -> LayoutAIClient:
    provider_env = os.getenv("PPTX_LLM_PROVIDER")
    base_provider = policy.provider.strip().lower() if policy.provider else "mock"
    provider = provider_env.strip().lower() if provider_env else base_provider
    logger.info(
        "layout AI provider resolved: env=%s policy=%s -> %s",
        provider_env or "",
        base_provider,
        provider,
    )
    if provider in {"mock", ""}:
        return MockLayoutAIClient()
    if provider in {"openai", "openai-api"}:
        return OpenAIChatLayoutClient.from_env(policy)
    if provider in {"azure", "azure-openai"}:
        return AzureOpenAIChatLayoutClient.from_env(policy)
    if provider in {"claude", "anthropic"}:
        return AnthropicClaudeLayoutClient.from_env(policy)
    if provider in {"aws-claude", "bedrock"}:
        return AwsClaudeLayoutClient.from_env(policy)
    raise LayoutAIClientConfigurationError(f"未知のレイアウトAIプロバイダが指定されました: {provider}")


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
            "model": request.policy.model,
            "recommended": [{"layout_id": layout, "score": score} for layout, score in weights],
            "reasons": reasons,
            "classifications": {key: list(value) for key, value in classifications.items()},
        }
        raw_text = json.dumps(payload, ensure_ascii=False)
        return LayoutAIResponse(
            model=request.policy.model,
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
    def from_env(cls, policy: LayoutAIPolicy) -> "OpenAIChatLayoutClient":
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            msg = "openai パッケージをインストールしてください (`pip install openai`)."
            raise LayoutAIClientConfigurationError(msg) from exc

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LayoutAIClientConfigurationError("OPENAI_API_KEY が設定されていません")

        base_url = os.getenv("OPENAI_BASE_URL")
        temperature = float(os.getenv("OPENAI_TEMPERATURE", str(policy.temperature or 0.0)))
        max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", str(policy.max_tokens or DEFAULT_MAX_TOKENS)))
        client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        model_name = policy.model or os.getenv("OPENAI_MODEL", "gpt-5-mini")
        if model_name in {"mock", "mock-local", "mock-layout"}:
            model_name = os.getenv("OPENAI_MODEL", "gpt-5-mini")
        return cls(client, model=model_name, temperature=temperature, max_tokens=max_tokens)

    def recommend(self, request: LayoutAIRequest) -> LayoutAIResponse:
        from openai.types.responses import ResponseOutputMessage, ResponseOutputRefusal, ResponseOutputText

        messages = [
            {"role": "system", "content": _build_system_prompt(request)},
            {"role": "user", "content": _build_user_prompt(request)},
        ]
        base_kwargs: dict[str, object] = {
            "input": messages,
            "temperature": self._temperature,
            "response_format": {"type": "json_object"},
        }
        if self._max_tokens > 0:
            base_kwargs["max_output_tokens"] = self._max_tokens

        candidate_models: list[str] = []
        for value in (
            request.policy.model,
            os.getenv("OPENAI_MODEL"),
            self._model,
            os.getenv("OPENAI_FALLBACK_MODEL"),
            "gpt-4o-mini",
            "gpt-4o-mini-2024-07-18",
        ):
            if not value:
                continue
            normalized = value.strip()
            if normalized in {"", "mock", "mock-local", "mock-layout"}:
                continue
            if normalized not in candidate_models:
                candidate_models.append(normalized)
        if not candidate_models:
            candidate_models.append(self._model)

        for model_name in candidate_models:
            attempt_kwargs = dict(base_kwargs)
            attempt_kwargs["model"] = model_name
            expanded_tokens = False
            removed_response_format = False
            while True:
                try:
                    response = self._client.responses.create(**attempt_kwargs)  # type: ignore[attr-defined]
                except Exception as exc:
                    message = str(exc)
                    if isinstance(exc, TypeError) and "response_format" in message and "unexpected" in message.lower():
                        attempt_kwargs.pop("response_format", None)
                        removed_response_format = True
                        logger.debug(
                            "retrying OpenAI layout completion without response_format (model=%s)",
                            model_name,
                        )
                        continue
                    logger.warning(
                        "OpenAI layout request failed for model '%s': %s",
                        model_name,
                        exc,
                    )
                    break

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
                content = "\n".join(segment.strip() for segment in text_segments if segment.strip())

                parse_failed = False
                parsed_response: LayoutAIResponse | None = None
                if content:
                    try:
                        parsed_response = _parse_layout_response(content, model=model_name)
                    except LayoutAIResponseFormatError as exc:
                        parse_failed = True
                        logger.debug(
                            "OpenAI layout response parse failed (model=%s): %s",
                            model_name,
                            exc,
                        )
                else:
                    logger.debug(
                        "OpenAI layout completion produced no content (status=%s model=%s) kwargs=%s",
                        getattr(response, "status", None),
                        model_name,
                        attempt_kwargs,
                    )

                if parsed_response and parsed_response.recommended:
                    return parsed_response

                if (incomplete or parse_failed) and not expanded_tokens and "max_output_tokens" in attempt_kwargs:
                    value = attempt_kwargs.get("max_output_tokens")
                    try:
                        current = int(value) if value is not None else self._max_tokens
                    except (TypeError, ValueError):
                        current = self._max_tokens
                    attempt_kwargs["max_output_tokens"] = min((current or self._max_tokens or DEFAULT_MAX_TOKENS) * 2, 4096)
                    expanded_tokens = True
                    logger.debug(
                        "retrying OpenAI layout completion with expanded max_output_tokens=%s (model=%s)",
                        attempt_kwargs["max_output_tokens"],
                        model_name,
                    )
                    continue

                if parse_failed and not removed_response_format and "response_format" in attempt_kwargs:
                    attempt_kwargs.pop("response_format", None)
                    removed_response_format = True
                    logger.debug(
                        "retrying OpenAI layout completion after removing response_format (model=%s)",
                        model_name,
                    )
                    continue

                if parsed_response and not parsed_response.recommended:
                    logger.debug("OpenAI layout model %s returned no recommendations", model_name)
                    break

                if parse_failed:
                    logger.warning(
                        "OpenAI layout model %s returned unparsable content after fallbacks",
                        model_name,
                    )
                    break
                if incomplete:
                    logger.debug("OpenAI layout model %s produced no usable content", model_name)
                    break

                break
        raise LayoutAIClientConfigurationError("OpenAI 応答が空でした")


class AzureOpenAIChatLayoutClient:
    """Azure OpenAI Chat Completions API を利用したレイアウト推薦。"""

    def __init__(self, client, *, deployment: str, temperature: float, max_tokens: int) -> None:
        self._client = client
        self._deployment = deployment
        self._temperature = temperature
        self._max_tokens = max_tokens

    @classmethod
    def from_env(cls, policy: LayoutAIPolicy) -> "AzureOpenAIChatLayoutClient":
        try:
            from openai import AzureOpenAI
        except ImportError as exc:  # pragma: no cover - optional dependency
            msg = "openai パッケージをインストールしてください (`pip install openai`)."
            raise LayoutAIClientConfigurationError(msg) from exc

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        deployment = policy.model or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if deployment in {"mock", "mock-local", "mock-layout", None}:
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if not endpoint or not api_key or not deployment:
            raise LayoutAIClientConfigurationError(
                "AZURE_OPENAI_ENDPOINT/AZURE_OPENAI_API_KEY/AZURE_OPENAI_DEPLOYMENT を設定してください"
            )
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        temperature = float(os.getenv("AZURE_OPENAI_TEMPERATURE", str(policy.temperature or 0.0)))
        max_tokens = int(os.getenv("AZURE_OPENAI_MAX_TOKENS", str(policy.max_tokens or DEFAULT_MAX_TOKENS)))
        endpoint = endpoint.rstrip("/")
        lowered = endpoint.lower()
        for suffix in ("/openai/responses", "/openai"):
            if lowered.endswith(suffix):
                endpoint = endpoint[: -len(suffix)]
                lowered = endpoint.lower()
        client = AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)
        return cls(client, deployment=deployment, temperature=temperature, max_tokens=max_tokens)

    def recommend(self, request: LayoutAIRequest) -> LayoutAIResponse:
        from openai.types.responses import ResponseOutputMessage
        from openai.types.responses.response_output_text import ResponseOutputText
        from openai.types.responses.response_output_refusal import ResponseOutputRefusal

        messages = [
            {"role": "system", "content": _build_system_prompt(request)},
            {"role": "user", "content": _build_user_prompt(request)},
        ]
        request_model = request.policy.model or self._deployment
        if request_model in {"mock", "mock-local", "mock-layout"}:
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

    def __init__(self, client, *, model: str, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    @classmethod
    def from_env(cls, policy: LayoutAIPolicy) -> "AnthropicClaudeLayoutClient":
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - optional dependency
            msg = "anthropic パッケージが必要です。`pip install anthropic` を実行してください。"
            raise LayoutAIClientConfigurationError(msg) from exc

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise LayoutAIClientConfigurationError("ANTHROPIC_API_KEY が設定されていません")
        model_id = policy.model or os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        if model_id in {"mock", "mock-local", "mock-layout"}:
            model_id = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS", str(policy.max_tokens or DEFAULT_MAX_TOKENS)))
        client = anthropic.Anthropic(api_key=api_key)
        return cls(client, model=model_id, max_tokens=max_tokens)

    def recommend(self, request: LayoutAIRequest) -> LayoutAIResponse:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": _build_user_prompt(request),
                    }
                ],
            }
        ]
        candidate_models: list[str] = []
        for value in (
            request.policy.model,
            os.getenv("ANTHROPIC_MODEL"),
            self._model,
            os.getenv("ANTHROPIC_FALLBACK_MODEL"),
            "claude-3-haiku-20240307",
        ):
            if not value:
                continue
            normalized = value.strip()
            if normalized in {"", "mock", "mock-local", "mock-layout"}:
                continue
            if normalized not in candidate_models:
                candidate_models.append(normalized)

        temperature = float(os.getenv("ANTHROPIC_TEMPERATURE", str(request.policy.temperature or 0.0)))
        last_error: Exception | None = None
        for candidate in candidate_models:
            try:
                response = self._client.messages.create(  # type: ignore[attr-defined]
                    model=candidate,
                    system=_build_system_prompt(request),
                    max_tokens=self._max_tokens,
                    temperature=temperature,
                    messages=messages,
                )
                model_name = candidate
                break
            except Exception as exc:  # pragma: no cover - best effort retries
                from anthropic import APIStatusError

                last_error = exc
                if isinstance(exc, APIStatusError):
                    logger.info(
                        "Anthropic layout AI request failed for model '%s': %s",
                        candidate,
                        exc,
                    )
                    continue
                raise
        else:  # no break
            raise LayoutAIClientConfigurationError(
                f"Anthropic API error: {last_error}"
            ) from last_error
        text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        content = "\n".join(text_parts)
        if not content:
            raise LayoutAIClientConfigurationError("Anthropic 応答が空でした")
        try:
            return _parse_layout_response(content, model=model_name)
        except LayoutAIResponseFormatError as exc:
            logger.debug("Anthropic layout response parse failed: %s", exc)
            return LayoutAIResponse(model=model_name, raw_text=content)


class AwsClaudeLayoutClient:
    """AWS Bedrock Claude を利用したレイアウト推薦。"""

    def __init__(self, runtime_client, *, model_id: str, max_tokens: int, inference_profile_arn: str | None) -> None:
        self._client = runtime_client
        self._model_id = model_id
        self._max_tokens = max_tokens
        self._inference_profile_arn = inference_profile_arn

    @classmethod
    def from_env(cls, policy: LayoutAIPolicy) -> "AwsClaudeLayoutClient":
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError
        except ImportError as exc:  # pragma: no cover - optional dependency
            msg = "boto3 パッケージが必要です。`pip install boto3` を実行してください。"
            raise LayoutAIClientConfigurationError(msg) from exc

        model_id = policy.model or os.getenv("AWS_CLAUDE_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        if model_id in {"mock", "mock-local", "mock-layout"}:
            model_id = os.getenv("AWS_CLAUDE_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        inference_profile_arn = os.getenv("AWS_CLAUDE_INFERENCE_PROFILE_ARN")
        region = os.getenv("AWS_REGION")
        profile = os.getenv("AWS_PROFILE")

        session_kwargs: dict[str, object] = {}
        if profile:
            session_kwargs["profile_name"] = profile
        if region:
            session_kwargs["region_name"] = region
        session = boto3.Session(**session_kwargs)
        credentials = session.get_credentials()
        if credentials is None:
            raise LayoutAIClientConfigurationError(
                "AWS 認証情報が見つかりません。環境変数や共有クレデンシャルで設定してください。"
            )

        client_kwargs: dict[str, object] = {}
        if region:
            client_kwargs["region_name"] = region
        try:
            runtime_client = session.client("bedrock-runtime", **client_kwargs)
        except NoCredentialsError as exc:
            raise LayoutAIClientConfigurationError(
                "AWS 認証情報を利用できません。AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY を設定してください。"
            ) from exc

        max_tokens = int(os.getenv("AWS_CLAUDE_MAX_TOKENS", str(policy.max_tokens or DEFAULT_MAX_TOKENS)))
        return cls(runtime_client, model_id=model_id, max_tokens=max_tokens, inference_profile_arn=inference_profile_arn)

    def recommend(self, request: LayoutAIRequest) -> LayoutAIResponse:
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self._max_tokens,
            "temperature": float(os.getenv("AWS_CLAUDE_TEMPERATURE", str(request.policy.temperature or 0.0))),
            "system": _build_system_prompt(request),
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": _build_user_prompt(request),
                        }
                    ],
                }
            ],
        }
        model_id = request.policy.model or self._model_id
        if model_id in {"mock", "mock-local", "mock-layout"}:
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
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


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


def _build_system_prompt(request: LayoutAIRequest) -> str:
    return (
        "あなたは B2B プレゼン資料のレイアウト推薦エージェントです。"
        "入力される JSON 情報を解析し、最も適したレイアウトを高精度に提案してください。"
        "応答は JSON オブジェクトのみで返し、次のスキーマを厳守してください: "
        '{"recommended":[{"layout_id":"<候補ID>","score":0.0,"tags":["title"]}],"reasons":{"<候補ID>":"根拠"}}.'
        "tags には入力で指定された allowed_tags の語彙を使用し、score は 0〜1 の範囲で数値にしてください。"
        "recommended 以外のキーやコードフェンス、説明文は含めてはいけません。"
    )


def _build_user_prompt(request: LayoutAIRequest) -> str:
    payload = {
        "card": request.card_payload,
        "candidate_layouts": request.layout_candidates,
        "instruction": request.prompt,
    }
    if request.layout_metadata:
        payload["layout_metadata"] = request.layout_metadata
    return json.dumps(payload, ensure_ascii=False)
