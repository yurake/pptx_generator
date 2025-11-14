"""テンプレート usage_tags 推定用 AI クライアント。"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Protocol

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


def create_template_ai_client(policy: TemplateAIPolicy) -> TemplateAIClient:
    """ポリシー設定から適切なクライアントを生成する。"""

    provider_env = os.getenv("PPTX_TEMPLATE_LLM_PROVIDER") or os.getenv("PPTX_LLM_PROVIDER")
    if provider_env:
        provider = provider_env.strip().lower()
    else:
        provider = "mock"
    logger.info(
        "template AI provider resolved: env=%s policy=%s -> %s",
        provider_env or "",
        "env",
        provider,
    )
    if provider in {"mock", ""}:
        return MockTemplateAIClient()
    if provider in {"openai", "openai-api"}:
        return OpenAITemplateAIClient.from_env(policy)
    if provider in {"azure", "azure-openai"}:
        return AzureOpenAITemplateAIClient.from_env(policy)
    if provider in {"claude", "anthropic"}:
        return AnthropicClaudeTemplateAIClient.from_env(policy)
    if provider in {"aws-claude", "bedrock"}:
        return AwsClaudeTemplateAIClient.from_env(policy)
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
            reason="heuristic-fallback",
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
        max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", str(policy.max_tokens or 512)))
        client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        model_name = policy.model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if model_name in {"mock", "mock-local", "mock-template"}:
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
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

        raw_text: str | None = None
        usage_tags: tuple[str, ...] | None = None
        reason: str | None = None
        for item in getattr(response, "output", []) or []:
            if isinstance(item, ResponseOutputMessage):
                for content in item.content:
                    if isinstance(content, ResponseOutputText):
                        raw_text = content.text
                        try:
                            data = json.loads(raw_text)
                        except json.JSONDecodeError:
                            continue
                        tags = data.get("usage_tags")
                        reason = data.get("reason")
                        if isinstance(tags, list):
                            canonical = normalize_usage_tags(tags)
                            usage_tags = canonical
        return TemplateAIResponse(
            model=self._model,
            usage_tags=usage_tags,
            reason=reason,
            raw_text=raw_text,
        )


class AzureOpenAITemplateAIClient:
    """Azure OpenAI Responses API を利用したテンプレート分類。"""

    def __init__(
        self,
        client,
        *,
        deployment: str,
        api_version: str,
        temperature: float,
        max_tokens: int,
    ) -> None:
        self._client = client
        self._deployment = deployment
        self._api_version = api_version
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
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if not all([endpoint, api_key, deployment]):
            raise TemplateAIClientConfigurationError(
                "AZURE_OPENAI_ENDPOINT/AZURE_OPENAI_API_KEY/AZURE_OPENAI_DEPLOYMENT を設定してください"
            )

        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        temperature = float(os.getenv("AZURE_OPENAI_TEMPERATURE", str(policy.temperature or 0.0)))
        max_tokens = int(os.getenv("AZURE_OPENAI_MAX_TOKENS", str(policy.max_tokens or 512)))

        endpoint = endpoint.rstrip("/")
        lowered = endpoint.lower()
        for suffix in ("/openai/responses", "/openai"):
            if lowered.endswith(suffix):
                endpoint = endpoint[: -len(suffix)]
                lowered = endpoint.lower()

        client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)
        return cls(
            client,
            deployment=deployment,
            api_version=api_version,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def classify(self, request: TemplateAIRequest) -> TemplateAIResponse:
        from openai.types.responses import ResponseOutputMessage, ResponseOutputText

        messages = [
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": _build_user_prompt(request)},
        ]
        deployment = request.policy.model or self._deployment
        if deployment in {"mock", "mock-local", "mock-template"}:
            deployment = self._deployment

        kwargs: dict[str, object] = {
            "model": deployment,
            "input": messages,
            "temperature": self._temperature,
        }
        if self._max_tokens > 0:
            kwargs["max_output_tokens"] = self._max_tokens

        response = self._client.responses.create(  # type: ignore[attr-defined]
            **kwargs,
        )

        raw_text: str | None = None
        usage_tags: tuple[str, ...] | None = None
        reason: str | None = None
        for item in getattr(response, "output", []) or []:
            if isinstance(item, ResponseOutputMessage):
                for content in item.content:
                    if isinstance(content, ResponseOutputText):
                        raw_text = content.text
                        try:
                            data = json.loads(raw_text)
                        except json.JSONDecodeError:
                            continue
                        tags = data.get("usage_tags")
                        reason = data.get("reason")
                        if isinstance(tags, list):
                            canonical = normalize_usage_tags(tags)
                            usage_tags = canonical
        return TemplateAIResponse(
            model=deployment,
            usage_tags=usage_tags,
            reason=reason,
            raw_text=raw_text,
        )


class AnthropicClaudeTemplateAIClient:
    """Anthropic Claude API を利用したテンプレート分類。"""

    def __init__(self, client, *, model: str, max_tokens: int, temperature: float) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature

    @classmethod
    def from_env(cls, policy: TemplateAIPolicy) -> AnthropicClaudeTemplateAIClient:
        try:
            from anthropic import Anthropic
        except ImportError as exc:  # pragma: no cover - optional dependency
            msg = "anthropic パッケージが必要です。`pip install anthropic` を実行してください。"
            raise TemplateAIClientConfigurationError(msg) from exc

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise TemplateAIClientConfigurationError("ANTHROPIC_API_KEY が設定されていません")
        model = policy.model or os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS", str(policy.max_tokens or 512)))
        temperature = float(os.getenv("ANTHROPIC_TEMPERATURE", str(policy.temperature or 0.0)))
        client = Anthropic(api_key=api_key)
        return cls(client, model=model, max_tokens=max_tokens, temperature=temperature)

    def classify(self, request: TemplateAIRequest) -> TemplateAIResponse:
        model_name = request.policy.model or self._model
        if model_name in {"mock", "mock-local", "mock-template"}:
            model_name = self._model
        response = self._client.messages.create(  # type: ignore[attr-defined]
            model=model_name,
            system=_build_system_prompt(),
            max_tokens=self._max_tokens,
            temperature=self._temperature,
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

        text_parts = [
            block.text
            for block in getattr(response, "content", [])
            if getattr(block, "type", None) == "text"
        ]
        raw_text = "\n".join(part.strip() for part in text_parts if part.strip()) or None
        if not raw_text:
            return TemplateAIResponse(model=model_name, usage_tags=None, reason=None, raw_text=None)
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.warning("Anthropic response is not valid JSON: %s", raw_text)
            return TemplateAIResponse(model=model_name, usage_tags=None, reason=None, raw_text=raw_text)
        tags = data.get("usage_tags")
        reason = data.get("reason")
        usage_tags: tuple[str, ...] | None = None
        if isinstance(tags, list):
            usage_tags = normalize_usage_tags(tags)
        return TemplateAIResponse(
            model=model_name,
            usage_tags=usage_tags,
            reason=reason if isinstance(reason, str) else None,
            raw_text=raw_text,
        )


class AwsClaudeTemplateAIClient:
    """AWS Bedrock Claude API を利用したテンプレート分類。"""

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
    def from_env(cls, policy: TemplateAIPolicy) -> AwsClaudeTemplateAIClient:
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError
        except ImportError as exc:  # pragma: no cover - optional dependency
            msg = "boto3 パッケージが必要です。`pip install boto3` を実行してください。"
            raise TemplateAIClientConfigurationError(msg) from exc

        model_id = policy.model or os.getenv("AWS_CLAUDE_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
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
            raise TemplateAIClientConfigurationError(
                "AWS 認証情報が見つかりません。AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY を設定するか、`aws configure` を実行してください。"
            )

        client_kwargs: dict[str, object] = {}
        if region:
            client_kwargs["region_name"] = region
        try:
            runtime_client = session.client("bedrock-runtime", **client_kwargs)
        except NoCredentialsError as exc:
            raise TemplateAIClientConfigurationError(
                "AWS 認証情報を利用できません。環境変数または共有クレデンシャルで設定してください。"
            ) from exc

        max_tokens = int(os.getenv("AWS_CLAUDE_MAX_TOKENS", str(policy.max_tokens or 512)))
        temperature = float(os.getenv("AWS_CLAUDE_TEMPERATURE", str(policy.temperature or 0.0)))
        return cls(
            runtime_client,
            model_id=model_id,
            max_tokens=max_tokens,
            inference_profile_arn=inference_profile_arn,
            temperature=temperature,
        )

    def classify(self, request: TemplateAIRequest) -> TemplateAIResponse:
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
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
        model_id = request.policy.model or self._model_id
        if model_id in {"mock", "mock-local", "mock-template"}:
            model_id = self._model_id

        invoke_kwargs = {
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
        if isinstance(body_text, (bytes, bytearray)):
            body_text = body_text.decode("utf-8")
        if not body_text:
            return TemplateAIResponse(model=model_id, usage_tags=None, reason=None, raw_text=None)
        try:
            data = json.loads(body_text)
        except json.JSONDecodeError:
            logger.warning("AWS Claude response is not valid JSON: %s", body_text)
            return TemplateAIResponse(model=model_id, usage_tags=None, reason=None, raw_text=body_text)

        content = data.get("content") or []
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_value = item.get("text")
                if isinstance(text_value, str):
                    text_parts.append(text_value)
        raw_text = "\n".join(part.strip() for part in text_parts if part.strip()) or None
        if not raw_text:
            return TemplateAIResponse(model=model_id, usage_tags=None, reason=None, raw_text=body_text)
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.warning("AWS Claude textual output is not valid JSON: %s", raw_text)
            return TemplateAIResponse(model=model_id, usage_tags=None, reason=None, raw_text=raw_text)

        tags = parsed.get("usage_tags")
        reason = parsed.get("reason")
        usage_tags: tuple[str, ...] | None = None
        if isinstance(tags, list):
            usage_tags = normalize_usage_tags(tags)
        return TemplateAIResponse(
            model=model_id,
            usage_tags=usage_tags,
            reason=reason if isinstance(reason, str) else None,
            raw_text=raw_text,
        )


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
