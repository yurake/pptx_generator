"""テンプレート usage_tags 推定用 AI クライアント。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from pptx_generator.llm import (
    log_provider_resolution,
    resolve_llm_provider,
    load_anthropic_config,
    load_azure_openai_config,
    load_aws_claude_config,
    load_openai_chat_config,
)

from ..utils.usage_tags import CANONICAL_USAGE_TAGS, normalize_usage_tags
from .policy import TemplateAIPolicy, TemplateAIPolicyError
from .prompts import build_system_prompt, build_user_prompt

logger = logging.getLogger(__name__)
DEFAULT_MAX_TOKENS = 32000


@dataclass(slots=True)
class TemplateAIRequest:
    """テンプレート AI への分類リクエスト。"""

    prompt: str
    policy: TemplateAIPolicy
    payload: dict[str, object]


@dataclass(slots=True)
class TemplateAIResponse:
    """テンプレート AI からの応答。"""

    model: str
    usage_tags: tuple[str, ...] | None = None
    reason: str | None = None
    raw_text: str | None = None


class TemplateAIClient(Protocol):
    """テンプレート AI クライアントのインターフェース。"""

    def classify(self, request: TemplateAIRequest) -> TemplateAIResponse:
        """レイアウト構造から usage_tags を推定する。"""


class TemplateAIClientConfigurationError(RuntimeError):
    """テンプレート AI クライアントの設定エラー。"""


def create_template_ai_client() -> tuple[TemplateAIClient, str]:
    """ポリシー設定から適切なクライアントを生成し、利用プロバイダ名を返す。"""

    resolution = resolve_llm_provider(
        primary_env="PPTX_LLM_PROVIDER",
    )
    log_provider_resolution(
        logger,
        component="template_ai",
        resolution=resolution,
    )

    factories: dict[str, Callable[[], TemplateAIClient]] = {
        "mock": MockTemplateAIClient,
        "openai": OpenAITemplateAIClient.from_env,
        "azure-openai": AzureOpenAITemplateAIClient.from_env,
        "anthropic": AnthropicTemplateAIClient.from_env,
        "aws-claude": AwsClaudeTemplateAIClient.from_env,
    }

    factory = factories.get(resolution.provider)
    if factory is None:
        raise TemplateAIClientConfigurationError(
            f"テンプレートAIプロバイダ '{resolution.provider}' には対応していません"
        )

    return factory(), resolution.provider


class MockTemplateAIClient:
    """静的ルールまたはヒューリスティックによる疑似応答。"""

    def classify(self, request: TemplateAIRequest) -> TemplateAIResponse:
        payload = request.payload
        heuristic = payload.get("heuristic_usage_tags") or []
        canonical = normalize_usage_tags(heuristic)
        return TemplateAIResponse(
            model="mock-template",
            usage_tags=canonical,
            reason="heuristic",
            raw_text=json.dumps({"usage_tags": list(canonical)}, ensure_ascii=False),
        )


class OpenAITemplateAIClient:
    """OpenAI Responses API を利用したテンプレート分類。"""

    def __init__(self, client, *, model: str, temperature: float, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    @classmethod
    def from_env(cls) -> OpenAITemplateAIClient:
        from openai import OpenAI

        config = load_openai_chat_config(
            default_model="",
            default_temperature=0.0,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            error_cls=TemplateAIClientConfigurationError,
        )
        if not config.model:
            raise TemplateAIClientConfigurationError("OPENAI_MODEL が設定されていません")
        client = OpenAI(api_key=config.api_key, base_url=config.base_url) if config.base_url else OpenAI(api_key=config.api_key)
        return cls(client, model=config.model, temperature=config.temperature, max_tokens=config.max_tokens)

    def classify(self, request: TemplateAIRequest) -> TemplateAIResponse:
        from openai.types.responses import ResponseOutputMessage, ResponseOutputText

        messages = [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": build_user_prompt(request)},
        ]
        base_kwargs: dict[str, object] = {
            "input": messages,
            "model": self._model,
            "temperature": self._temperature,
            "response_format": {"type": "json_object"},
        }
        if self._max_tokens > 0:
            base_kwargs["max_output_tokens"] = self._max_tokens

        try:
            response = self._client.responses.create(**base_kwargs)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            raise TemplateAIClientConfigurationError(str(exc)) from exc

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("template AI raw response (provider=openai): %s", response)

        text_segments: list[str] = []
        for item in getattr(response, "output", []) or []:
            if isinstance(item, ResponseOutputMessage):
                for content in item.content:
                    if isinstance(content, ResponseOutputText):
                        text_segments.append(content.text)

        raw_text = "\n".join(segment.strip() for segment in text_segments if segment and segment.strip()) or None
        usage_tags, reason = _parse_template_ai_response(raw_text)
        return TemplateAIResponse(
            model=self._model,
            usage_tags=usage_tags,
            reason=reason,
            raw_text=raw_text,
        )


class AzureOpenAITemplateAIClient:
    """Azure OpenAI Responses API を利用したテンプレート分類。"""

    def __init__(self, client, *, deployment: str, temperature: float, max_tokens: int) -> None:
        self._client = client
        self._deployment = deployment
        self._temperature = temperature
        self._max_tokens = max_tokens

    @classmethod
    def from_env(cls) -> AzureOpenAITemplateAIClient:
        from openai import AzureOpenAI

        config = load_azure_openai_config(
            default_temperature=0.0,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            default_api_version="2024-02-15-preview",
            error_cls=TemplateAIClientConfigurationError,
        )

        client = AzureOpenAI(
            api_key=config.api_key,
            api_version=config.api_version,
            azure_endpoint=config.endpoint,
        )
        return cls(client, deployment=config.deployment, temperature=config.temperature, max_tokens=config.max_tokens)

    def classify(self, request: TemplateAIRequest) -> TemplateAIResponse:
        from openai.types.responses import ResponseOutputMessage, ResponseOutputRefusal, ResponseOutputText

        messages = [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": build_user_prompt(request)},
        ]
        kwargs: dict[str, object] = {
            "model": self._deployment,
            "input": messages,
            "temperature": self._temperature,
        }
        if self._max_tokens > 0:
            kwargs["max_output_tokens"] = self._max_tokens

        try:
            response = self._client.responses.create(**kwargs)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            raise TemplateAIClientConfigurationError(str(exc)) from exc

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("template AI raw response (provider=azure-openai): %s", response)

        text_segments: list[str] = []
        for item in getattr(response, "output", []) or []:
            if isinstance(item, ResponseOutputMessage):
                for content in item.content:
                    if isinstance(content, ResponseOutputText):
                        text_segments.append(content.text)
                    elif isinstance(content, ResponseOutputRefusal):  # pragma: no cover - refusal info only
                        logger.info("Azure OpenAI template AI refusal: %s", content.refusal)

        raw_text = "\n".join(segment.strip() for segment in text_segments if segment and segment.strip()) or None
        usage_tags, reason = _parse_template_ai_response(raw_text)
        return TemplateAIResponse(
            model=f"azure-openai:{self._deployment}",
            usage_tags=usage_tags,
            reason=reason,
            raw_text=raw_text,
        )


class AnthropicTemplateAIClient:
    """Anthropic Claude API を利用したテンプレート分類。"""

    def __init__(self, client, *, model: str, max_tokens: int, temperature: float) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature

    @classmethod
    def from_env(cls) -> AnthropicTemplateAIClient:
        import anthropic

        config = load_anthropic_config(
            default_model="claude-3-haiku-20240307",
            default_temperature=0.0,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            error_cls=TemplateAIClientConfigurationError,
        )
        client = anthropic.Anthropic(api_key=config.api_key)
        return cls(client, model=config.model, max_tokens=config.max_tokens, temperature=config.temperature)

    def classify(self, request: TemplateAIRequest) -> TemplateAIResponse:
        model_name = self._model or ""
        try:
            response = self._client.messages.create(  # type: ignore[attr-defined]
                model=model_name,
                system=build_system_prompt(),
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                messages=[
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
            )
        except Exception as exc:  # pragma: no cover - API failure
            logger.error(
                "Anthropic template AI request failed: model=%s payload_keys=%s error=%s",
                model_name,
                list(request.payload.keys()),
                exc,
            )
            raise TemplateAIClientConfigurationError(str(exc)) from exc

        text_parts = [
            block.text for block in response.content if getattr(block, "type", None) == "text" and getattr(block, "text", None)
        ]
        raw_text = "\n".join(part.strip() for part in text_parts if part.strip()) or None
        if raw_text is None:
            raise TemplateAIClientConfigurationError("Anthropic 応答が空でした")
        usage_tags, reason = _parse_template_ai_response(raw_text)
        return TemplateAIResponse(
            model=f"anthropic:{model_name}",
            usage_tags=usage_tags,
            reason=reason,
            raw_text=raw_text,
        )


class AwsClaudeTemplateAIClient:
    """AWS Bedrock Claude を利用したテンプレート分類。"""

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
    def from_env(cls) -> AwsClaudeTemplateAIClient:
        import boto3
        from botocore.exceptions import NoCredentialsError

        config = load_aws_claude_config(
            default_model_id="anthropic.claude-3-haiku-20240307-v1:0",
            default_temperature=0.0,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            error_cls=TemplateAIClientConfigurationError,
        )

        session_kwargs: dict[str, Any] = {}
        if config.profile:
            session_kwargs["profile_name"] = config.profile
        if config.region:
            session_kwargs["region_name"] = config.region

        session = boto3.Session(**session_kwargs)
        credentials = session.get_credentials()
        if credentials is None:
            raise TemplateAIClientConfigurationError(
                "AWS 認証情報が見つかりません。AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY を設定してください。"
            )

        client_kwargs: dict[str, Any] = {}
        if config.region:
            client_kwargs["region_name"] = config.region
        try:
            runtime_client = session.client("bedrock-runtime", **client_kwargs)
        except NoCredentialsError as exc:
            raise TemplateAIClientConfigurationError(
                "AWS 認証情報を利用できません。AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY を設定してください。"
            ) from exc

        return cls(
            runtime_client,
            model_id=config.model_id,
            max_tokens=config.max_tokens,
            inference_profile_arn=config.inference_profile_arn,
            temperature=config.temperature,
        )

    def classify(self, request: TemplateAIRequest) -> TemplateAIResponse:
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "system": build_system_prompt(),
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
        invoke_kwargs: dict[str, Any] = {
            "modelId": self._model_id,
            "body": json.dumps(payload),
            "contentType": "application/json",
            "accept": "application/json",
        }
        if self._inference_profile_arn:
            invoke_kwargs["inferenceProfileArn"] = self._inference_profile_arn

        response = self._client.invoke_model(**invoke_kwargs)
        body = response.get("body")
        body_text = body.read() if hasattr(body, "read") else body
        if isinstance(body_text, (bytes, bytearray)):
            body_text = body_text.decode("utf-8")
        try:
            data = json.loads(body_text)
        except (TypeError, json.JSONDecodeError) as exc:
            raise TemplateAIClientConfigurationError(f"AWS Claude 応答の解析に失敗しました: {exc}") from exc

        text_parts = [item.get("text", "") for item in data.get("content", []) if isinstance(item, dict)]
        raw_text = "\n".join(part.strip() for part in text_parts if isinstance(part, str) and part.strip()) or None
        if raw_text is None:
            raise TemplateAIClientConfigurationError("AWS Claude 応答が空でした")
        usage_tags, reason = _parse_template_ai_response(raw_text)
        return TemplateAIResponse(
            model=f"aws-claude:{self._model_id}",
            usage_tags=usage_tags,
            reason=reason,
            raw_text=raw_text,
        )


def _parse_template_ai_response(raw_text: str | None) -> tuple[tuple[str, ...] | None, str | None]:
    if not raw_text:
        return None, None
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        return None, None

    tags = data.get("usage_tags")
    canonical: tuple[str, ...] | None = None
    if isinstance(tags, (list, tuple)):
        canonical = normalize_usage_tags(tags)  # type: ignore[arg-type]

    reason = _stringify_reason(data.get("reason"))
    return canonical if canonical else None, reason


def _stringify_reason(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return str(value)
