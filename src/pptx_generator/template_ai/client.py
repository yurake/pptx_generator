"""テンプレート usage_tags 推定用 AI クライアント。"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Protocol

from ..utils.usage_tags import CANONICAL_USAGE_TAGS, normalize_usage_tags
from .policy import TemplateAIPolicy, TemplateAIPolicyError

logger = logging.getLogger(__name__)


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


def create_template_ai_client(policy: TemplateAIPolicy) -> tuple[TemplateAIClient, str]:
    """ポリシー設定から適切なクライアントを生成し、利用プロバイダ名を返す。"""

    provider_env = os.getenv("PPTX_TEMPLATE_LLM_PROVIDER") or os.getenv("PPTX_LLM_PROVIDER")
    provider = (provider_env or "mock").strip().lower() or "mock"
    logger.info(
        "template AI provider resolved: env=%s -> %s",
        provider_env or "",
        provider,
    )
    if provider in {"mock", ""}:
        return MockTemplateAIClient(), "mock"
    if provider in {"openai", "openai-api"}:
        return OpenAITemplateAIClient.from_env(policy), "openai"
    if provider in {"azure", "azure-openai"}:
        return AzureOpenAITemplateAIClient.from_env(policy), "azure-openai"
    if provider in {"claude", "anthropic"}:
        return AnthropicTemplateAIClient.from_env(policy), "anthropic"
    if provider in {"aws-claude", "bedrock"}:
        return AwsClaudeTemplateAIClient.from_env(policy), "aws-claude"
    raise TemplateAIClientConfigurationError(
        f"テンプレートAIプロバイダ '{provider}' には対応していません"
    )


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
    def from_env(cls, policy: TemplateAIPolicy) -> OpenAITemplateAIClient:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional dependency
            msg = "openai パッケージをインストールしてください (`pip install openai`)."
            raise TemplateAIClientConfigurationError(msg) from exc

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise TemplateAIClientConfigurationError("OPENAI_API_KEY が設定されていません")

        base_url = os.getenv("OPENAI_BASE_URL")
        temperature = float(os.getenv("OPENAI_TEMPERATURE", str(policy.temperature or 0.0)))
        max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", str(policy.max_tokens or 32000)))
        client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        model_name = os.getenv("OPENAI_MODEL")
        if not model_name:
            raise TemplateAIClientConfigurationError("OPENAI_MODEL が設定されていません")
        return cls(client, model=model_name, temperature=temperature, max_tokens=max_tokens)

    def classify(self, request: TemplateAIRequest) -> TemplateAIResponse:
        from openai.types.responses import ResponseOutputMessage, ResponseOutputText

        messages = [
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": _build_user_prompt(request)},
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
    def from_env(cls, policy: TemplateAIPolicy) -> AzureOpenAITemplateAIClient:
        try:
            from openai import AzureOpenAI
        except ImportError as exc:  # pragma: no cover - optional dependency
            msg = "openai パッケージが必要です。`pip install openai` を実行してください。"
            raise TemplateAIClientConfigurationError(msg) from exc

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not endpoint or not api_key:
            raise TemplateAIClientConfigurationError(
                "AZURE_OPENAI_ENDPOINT と AZURE_OPENAI_API_KEY を設定してください"
            )
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if not deployment:
            raise TemplateAIClientConfigurationError("AZURE_OPENAI_DEPLOYMENT が設定されていません")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        temperature = float(os.getenv("AZURE_OPENAI_TEMPERATURE", str(policy.temperature or 0.0)))
        max_tokens = int(os.getenv("AZURE_OPENAI_MAX_TOKENS", str(policy.max_tokens or 32000)))

        endpoint_clean = endpoint.rstrip("/")
        lowered = endpoint_clean.lower()
        for suffix in ("/openai/responses", "/openai"):
            if lowered.endswith(suffix):
                endpoint_clean = endpoint_clean[: -len(suffix)]
                lowered = endpoint_clean.lower()

        client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint_clean)
        return cls(client, deployment=deployment, temperature=temperature, max_tokens=max_tokens)

    def classify(self, request: TemplateAIRequest) -> TemplateAIResponse:
        from openai.types.responses import ResponseOutputMessage, ResponseOutputRefusal, ResponseOutputText

        messages = [
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": _build_user_prompt(request)},
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

    def __init__(self, client, *, model: str, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    @classmethod
    def from_env(cls, policy: TemplateAIPolicy) -> AnthropicTemplateAIClient:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - optional dependency
            msg = "anthropic パッケージが必要です。`pip install anthropic` を実行してください。"
            raise TemplateAIClientConfigurationError(msg) from exc

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise TemplateAIClientConfigurationError("ANTHROPIC_API_KEY が設定されていません")

        model_id = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS", str(policy.max_tokens or 32000)))
        client = anthropic.Anthropic(api_key=api_key)
        return cls(client, model=model_id, max_tokens=max_tokens)

    def classify(self, request: TemplateAIRequest) -> TemplateAIResponse:
        model_name = self._model or os.getenv("ANTHROPIC_MODEL") or ""
        temperature = float(os.getenv("ANTHROPIC_TEMPERATURE", str(request.policy.temperature or 0.0)))
        try:
            response = self._client.messages.create(  # type: ignore[attr-defined]
                model=model_name,
                system=_build_system_prompt(),
                max_tokens=self._max_tokens,
                temperature=temperature,
                messages=[
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

    def __init__(self, runtime_client, *, model_id: str, max_tokens: int, inference_profile_arn: str | None) -> None:
        self._client = runtime_client
        self._model_id = model_id
        self._max_tokens = max_tokens
        self._inference_profile_arn = inference_profile_arn

    @classmethod
    def from_env(cls, policy: TemplateAIPolicy) -> AwsClaudeTemplateAIClient:
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError
        except ImportError as exc:  # pragma: no cover - optional dependency
            msg = "boto3 パッケージが必要です。`pip install boto3` を実行してください。"
            raise TemplateAIClientConfigurationError(msg) from exc

        model_id = os.getenv("AWS_CLAUDE_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        inference_profile_arn = os.getenv("AWS_CLAUDE_INFERENCE_PROFILE_ARN")
        region = os.getenv("AWS_REGION")
        profile = os.getenv("AWS_PROFILE")

        session_kwargs: dict[str, Any] = {}
        if profile:
            session_kwargs["profile_name"] = profile
        if region:
            session_kwargs["region_name"] = region

        session = boto3.Session(**session_kwargs)
        credentials = session.get_credentials()
        if credentials is None:
            raise TemplateAIClientConfigurationError(
                "AWS 認証情報が見つかりません。AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY を設定してください。"
            )

        client_kwargs: dict[str, Any] = {}
        if region:
            client_kwargs["region_name"] = region
        try:
            runtime_client = session.client("bedrock-runtime", **client_kwargs)
        except NoCredentialsError as exc:
            raise TemplateAIClientConfigurationError(
                "AWS 認証情報を利用できません。AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY を設定してください。"
            ) from exc

        max_tokens = int(os.getenv("AWS_CLAUDE_MAX_TOKENS", str(policy.max_tokens or 32000)))
        return cls(runtime_client, model_id=model_id, max_tokens=max_tokens, inference_profile_arn=inference_profile_arn)

    def classify(self, request: TemplateAIRequest) -> TemplateAIResponse:
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self._max_tokens,
            "temperature": float(os.getenv("AWS_CLAUDE_TEMPERATURE", str(request.policy.temperature or 0.0))),
            "system": _build_system_prompt(),
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


def _build_system_prompt() -> str:
    return (
        "あなたは B2B プレゼン資料テンプレートを分析し、レイアウトの用途タグを判定するアシスタントです。"
        "必ず JSON オブジェクトのみで出力し、usage_tags に CANONICAL usage tags "
        f"({', '.join(sorted(CANONICAL_USAGE_TAGS))}) のみを含めてください。"
    )


def _build_user_prompt(request: TemplateAIRequest) -> str:
    payload = dict(request.payload)
    payload["instruction"] = request.prompt
    return json.dumps(payload, ensure_ascii=False, indent=2)
