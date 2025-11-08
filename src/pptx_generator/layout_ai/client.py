"""レイアウト推薦 AI クライアント。"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Protocol

from .policy import LayoutAIPolicy, LayoutAIPolicyError

logger = logging.getLogger(__name__)

_LAYOUT_LLM_LOGGER = logging.getLogger("pptx_generator.layout_ai.llm")
DEFAULT_MAX_TOKENS = 256


@dataclass(slots=True)
class LayoutAIRequest:
    """レイアウト推薦 AI へのリクエスト。"""

    prompt: str
    policy: LayoutAIPolicy
    card_payload: dict[str, object]
    layout_candidates: list[str]


@dataclass(slots=True)
class LayoutAIResponse:
    """レイアウト推薦 AI からの応答。"""

    model: str
    recommended: list[tuple[str, float]] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)
    raw_text: str | None = None


class LayoutAIClient(Protocol):
    """レイアウト推薦 AI クライアントのインターフェース。"""

    def recommend(self, request: LayoutAIRequest) -> LayoutAIResponse:
        """カード情報からレイアウト候補を評価する。"""


class LayoutAIClientConfigurationError(RuntimeError):
    """クライアント設定のエラー。"""


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
        payload = {
            "model": request.policy.model,
            "recommended": [{"layout_id": layout, "score": score} for layout, score in weights],
            "reasons": reasons,
        }
        raw_text = json.dumps(payload, ensure_ascii=False)
        return LayoutAIResponse(
            model=request.policy.model,
            recommended=weights,
            reasons=reasons,
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
        messages = [
            {"role": "system", "content": _build_system_prompt(request)},
            {"role": "user", "content": _build_user_prompt(request)},
        ]
        kwargs: dict[str, object] = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "response_format": {"type": "json_object"},
        }
        if self._max_tokens > 0:
            kwargs["max_completion_tokens"] = self._max_tokens

        response = self._client.chat.completions.create(**kwargs)  # type: ignore[attr-defined]
        choice = response.choices[0]
        message = choice.message
        content = getattr(message, "content", None)
        if not isinstance(content, str):
            raise LayoutAIClientConfigurationError("LLM 応答が文字列ではありません")
        return _parse_layout_response(content, model=self._model)


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
        if self._max_tokens > 0:
            kwargs["max_output_tokens"] = self._max_tokens

        response = self._client.responses.create(**kwargs)  # type: ignore[attr-defined]
        text_segments: list[str] = []
        for item in getattr(response, "output", []) or []:
            if isinstance(item, ResponseOutputMessage):
                for content in item.content:
                    if isinstance(content, ResponseOutputText):
                        text_segments.append(content.text)
                    elif isinstance(content, ResponseOutputRefusal):  # pragma: no cover - refusal path
                        logger.warning("Azure OpenAI layout AI refusal: %s", content.refusal)
        content = "\n".join(segment.strip() for segment in text_segments if segment.strip())
        if not content:
            raise LayoutAIClientConfigurationError("Azure OpenAI 応答が空でした")
        return _parse_layout_response(content, model=request_model)


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
                    logger.warning(
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
        return _parse_layout_response(content, model=model_name)


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
        return _parse_layout_response(content, model=model_id)


def _parse_layout_response(text: str, *, model: str) -> LayoutAIResponse:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LayoutAIClientConfigurationError("LLM 応答が JSON 形式ではありません") from exc
    entries: list[tuple[str, float]] = []
    for item in data.get("recommended", []):
        if not isinstance(item, dict):
            continue
        layout_id = item.get("layout_id")
        score = item.get("score")
        if isinstance(layout_id, str):
            entries.append((layout_id, float(score) if score is not None else 0.0))
    reasons = {
        str(k): str(v)
        for k, v in (data.get("reasons") or {}).items()
        if isinstance(k, str)
    }
    return LayoutAIResponse(
        model=model,
        recommended=entries,
        reasons=reasons,
        raw_text=text,
    )


def _build_system_prompt(request: LayoutAIRequest) -> str:
    return (
        "あなたは B2B プレゼン資料のレイアウト推薦エージェントです。"
        "入力される JSON 情報を解析し、最も適したレイアウトを高精度に提案してください。"
        "応答は JSON オブジェクトのみで返してください。"
    )


def _build_user_prompt(request: LayoutAIRequest) -> str:
    payload = {
        "card": request.card_payload,
        "candidate_layouts": request.layout_candidates,
        "instruction": request.prompt,
    }
    return json.dumps(payload, ensure_ascii=False)
