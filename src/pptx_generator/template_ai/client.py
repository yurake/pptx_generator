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

    provider_env = os.getenv("PPTX_TEMPLATE_LLM_PROVIDER")
    base_provider = policy.provider.strip().lower() if policy.provider else "mock"
    provider = provider_env.strip().lower() if provider_env else base_provider
    logger.info(
        "template AI provider resolved: env=%s policy=%s -> %s",
        provider_env or "",
        base_provider,
        provider,
    )
    if provider in {"mock", ""}:
        return MockTemplateAIClient()
    if provider in {"openai", "openai-api"}:
        return OpenAITemplateAIClient.from_env(policy)
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
