"""生成 AI クライアントの抽象化と実装集。"""

from __future__ import annotations

import json
import logging
import os
import re
import textwrap
from dataclasses import dataclass, field
from typing import Protocol

from ..models import JobSpec, Slide
from .policy import ContentAIPolicy

logger = logging.getLogger(__name__)

MAX_BODY_LINES = 6
MAX_BODY_LENGTH = 40
MAX_TITLE_LENGTH = 120
DEFAULT_MAX_TOKENS = 1024


class LLMClientConfigurationError(RuntimeError):
    """LLM クライアントの初期化に失敗した場合の例外。"""


@dataclass(slots=True)
class AIGenerationRequest:
    """LLM へのリクエスト。"""

    prompt: str
    policy: ContentAIPolicy
    spec: JobSpec
    slide: Slide
    intent: str


@dataclass(slots=True)
class AIGenerationResponse:
    """LLM からの応答。"""

    title: str
    body: list[str] = field(default_factory=list)
    note: str | None = None
    intent: str | None = None
    model: str = "mock-local"
    warnings: list[str] = field(default_factory=list)


class LLMClient(Protocol):
    """生成 AI クライアント共通インターフェース。"""

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        """リクエストに基づきスライド候補を生成する。"""


def create_llm_client() -> LLMClient:
    """環境変数に基づき LLM クライアントを生成する。"""

    provider = os.getenv("PPTX_LLM_PROVIDER", "mock").strip().lower()
    if provider in {"", "mock", "mock-local"}:
        return MockLLMClient()
    if provider in {"openai", "openai-api"}:
        return OpenAIChatClient.from_env()
    if provider in {"azure-openai", "azure"}:
        return AzureOpenAIChatClient.from_env()
    if provider in {"claude", "anthropic"}:
        return AnthropicClaudeClient.from_env()
    if provider in {"aws-claude", "bedrock"}:
        return AwsClaudeClient.from_env()
    msg = f"未知の LLM プロバイダーが指定されました: {provider}"
    raise LLMClientConfigurationError(msg)


def _truncate(value: str, max_length: int) -> str:
    normalized = value.strip()
    if len(normalized) <= max_length:
        return normalized
    ellipsis = "..."
    if max_length <= len(ellipsis):
        return ellipsis[:max_length]
    return normalized[: max_length - len(ellipsis)] + ellipsis


def _normalize_body(candidates: list[str]) -> tuple[list[str], list[str]]:
    """本文候補を正規化し、長さ制限を満たすように整形する。"""

    body_lines: list[str] = []
    warnings: list[str] = []

    for candidate in candidates:
        text = str(candidate).strip()
        if not text:
            continue
        if len(body_lines) >= MAX_BODY_LINES:
            warnings.append("body_lines_truncated")
            break
        if len(text) > MAX_BODY_LENGTH:
            warnings.append("body_line_length_truncated")
            text = text[:MAX_BODY_LENGTH]
        body_lines.append(text)

    if not body_lines:
        body_lines.append("自動生成コンテンツ")

    return body_lines, warnings


def _build_user_prompt(request: AIGenerationRequest) -> str:
    instructions = request.policy.safeguards.get("user_instructions") if isinstance(request.policy.safeguards, dict) else None
    guidance = instructions or textwrap.dedent(
        """
        以下の要件を必ず守って JSON 形式で回答してください。
        - JSON オブジェクトのキーは title, body, note。
        - body は文字列の配列で最大6行、各行40文字以内。
        - note が不要な場合は null を指定。
        - 日本語で回答する。
        """
    ).strip()
    return f"{guidance}\n\n# スライド情報\n{request.prompt}"


def _build_system_prompt(request: AIGenerationRequest) -> str:
    safeguards = request.policy.safeguards if isinstance(request.policy.safeguards, dict) else {}
    default_prompt = "あなたは B2B プレゼン資料のコンテンツ作成を支援する専門アシスタントです。"
    return str(safeguards.get("system_prompt", default_prompt))


def _extract_json_from_text(text: str) -> dict[str, object]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _build_response_from_text(
    text: str,
    request: AIGenerationRequest,
    *,
    model: str,
) -> AIGenerationResponse:
    warnings: list[str] = []
    data: dict[str, object]
    try:
        data = _extract_json_from_text(text)
    except json.JSONDecodeError:
        warnings.append("response_not_json")
        lines = [line.strip("-• ") for line in text.splitlines() if line.strip()]
        title_source = lines[0] if lines else request.slide.title or request.prompt
        body_candidates = lines[1:] if len(lines) > 1 else lines
        body, body_warnings = _normalize_body(body_candidates)
        warnings.extend(body_warnings)
        return AIGenerationResponse(
            title=_truncate(title_source, MAX_TITLE_LENGTH),
            body=body,
            note=None,
            intent=request.intent,
            model=model,
            warnings=warnings,
        )

    title_source = data.get("title") or request.slide.title or request.spec.meta.title
    body_candidates = data.get("body")
    if isinstance(body_candidates, list):
        body_raw = [str(item) for item in body_candidates]
    elif body_candidates is None:
        body_raw = []
    else:
        body_raw = [str(body_candidates)]
        warnings.append("body_not_array")

    body, body_warnings = _normalize_body(body_raw)
    warnings.extend(body_warnings)

    note_value = data.get("note")
    note = None if note_value in (None, "", "null") else str(note_value)

    intent_value = data.get("intent")
    intent = str(intent_value) if isinstance(intent_value, str) else request.intent

    return AIGenerationResponse(
        title=_truncate(str(title_source), MAX_TITLE_LENGTH),
        body=body,
        note=note,
        intent=intent,
        model=model,
        warnings=warnings,
    )


class MockLLMClient:
    """開発用のモック LLM クライアント。"""

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        slide = request.slide
        title_source = slide.title or f"{request.spec.meta.title} ({slide.id})"
        title = _truncate(title_source, MAX_TITLE_LENGTH)

        bullet_texts: list[str] = []
        for group in slide.iter_bullet_groups():
            for item in group.items:
                bullet_texts.append(item.text)

        if not bullet_texts:
            bullet_texts.append(request.prompt)

        body, warnings = _normalize_body(bullet_texts)
        note = (
            f"{request.policy.name} ポリシーを使用して自動生成しました。"
            if request.policy.name
            else None
        )

        return AIGenerationResponse(
            title=title,
            body=body,
            note=note,
            intent=request.intent,
            model=request.policy.model,
            warnings=warnings,
        )


class OpenAIChatClient:
    """OpenAI Chat Completions API クライアント。"""

    def __init__(self, client, *, model: str, temperature: float, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    @classmethod
    def from_env(cls) -> "OpenAIChatClient":
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - missing optional dependency
            msg = "openai パッケージが必要です。`pip install openai` を実行してください。"
            raise LLMClientConfigurationError(msg) from exc

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMClientConfigurationError("OPENAI_API_KEY が設定されていません")

        base_url = os.getenv("OPENAI_BASE_URL")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
        max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
        client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        return cls(client, model=model, temperature=temperature, max_tokens=max_tokens)

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        messages = [
            {"role": "system", "content": _build_system_prompt(request)},
            {"role": "user", "content": _build_user_prompt(request)},
        ]
        model_name = request.policy.model or self._model
        response = self._client.chat.completions.create(  # type: ignore[attr-defined]
            model=model_name,
            messages=messages,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        content = response.choices[0].message.content  # type: ignore[index]
        text = content if isinstance(content, str) else "".join(content)
        return _build_response_from_text(text, request, model=model_name)


class AzureOpenAIChatClient:
    """Azure OpenAI Chat Completions API クライアント。"""

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
    def from_env(cls) -> "AzureOpenAIChatClient":
        try:
            from openai import AzureOpenAI
        except ImportError as exc:  # pragma: no cover - missing optional dependency
            msg = "openai パッケージが必要です。`pip install openai` を実行してください。"
            raise LLMClientConfigurationError(msg) from exc

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        if not all([endpoint, api_key, deployment]):
            raise LLMClientConfigurationError(
                "AZURE_OPENAI_ENDPOINT/AZURE_OPENAI_API_KEY/AZURE_OPENAI_DEPLOYMENT を設定してください"
            )
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        temperature = float(os.getenv("AZURE_OPENAI_TEMPERATURE", "0.3"))
        max_tokens = int(os.getenv("AZURE_OPENAI_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
        client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)
        return cls(client, deployment=deployment, api_version=api_version, temperature=temperature, max_tokens=max_tokens)

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        messages = [
            {"role": "system", "content": _build_system_prompt(request)},
            {"role": "user", "content": _build_user_prompt(request)},
        ]
        deployment = request.policy.model or self._deployment
        response = self._client.chat.completions.create(  # type: ignore[attr-defined]
            model=deployment,
            messages=messages,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        content = response.choices[0].message.content  # type: ignore[index]
        text = content if isinstance(content, str) else "".join(content)
        return _build_response_from_text(text, request, model=deployment)


class AnthropicClaudeClient:
    """Anthropic Claude API クライアント。"""

    def __init__(self, client, *, model: str, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    @classmethod
    def from_env(cls) -> "AnthropicClaudeClient":
        try:
            from anthropic import Anthropic
        except ImportError as exc:  # pragma: no cover - missing optional dependency
            msg = "anthropic パッケージが必要です。`pip install anthropic` を実行してください。"
            raise LLMClientConfigurationError(msg) from exc

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMClientConfigurationError("ANTHROPIC_API_KEY が設定されていません")
        model = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
        client = Anthropic(api_key=api_key)
        return cls(client, model=model, max_tokens=max_tokens)

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
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
        response = self._client.messages.create(  # type: ignore[attr-defined]
            model=request.policy.model or self._model,
            system=_build_system_prompt(request),
            max_tokens=self._max_tokens,
            temperature=float(os.getenv("ANTHROPIC_TEMPERATURE", "0.3")),
            messages=messages,
        )
        text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        text = "\n".join(text_parts)
        model_name = request.policy.model or self._model
        return _build_response_from_text(text, request, model=model_name)


class AwsClaudeClient:
    """AWS Bedrock Claude クライアント。"""

    def __init__(self, runtime_client, *, model_id: str, max_tokens: int) -> None:
        self._client = runtime_client
        self._model_id = model_id
        self._max_tokens = max_tokens

    @classmethod
    def from_env(cls) -> "AwsClaudeClient":
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - missing optional dependency
            msg = "boto3 パッケージが必要です。`pip install boto3` を実行してください。"
            raise LLMClientConfigurationError(msg) from exc

        model_id = os.getenv("AWS_CLAUDE_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
        region = os.getenv("AWS_REGION")
        runtime_client = boto3.client("bedrock-runtime", region_name=region) if region else boto3.client("bedrock-runtime")
        max_tokens = int(os.getenv("AWS_CLAUDE_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
        return cls(runtime_client, model_id=model_id, max_tokens=max_tokens)

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self._max_tokens,
            "temperature": float(os.getenv("AWS_CLAUDE_TEMPERATURE", "0.3")),
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
        response = self._client.invoke_model(
            modelId=model_id,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json",
        )
        body = response.get("body")
        if hasattr(body, "read"):
            body_text = body.read()
        else:  # pragma: no cover - unexpected response type
            body_text = body
        data = json.loads(body_text)
        contents = data.get("content", [])
        text_parts = [item.get("text", "") for item in contents if isinstance(item, dict)]
        text = "\n".join(text_parts)
        return _build_response_from_text(text, request, model=model_id)


__all__ = [
    "AIGenerationRequest",
    "AIGenerationResponse",
    "LLMClient",
    "LLMClientConfigurationError",
    "MockLLMClient",
    "create_llm_client",
]
