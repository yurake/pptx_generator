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
        data = json.loads(content)
        entries = []
        for item in data.get("recommended", []):
            layout_id = item.get("layout_id")
            score = item.get("score")
            if isinstance(layout_id, str):
                entries.append((layout_id, float(score) if score is not None else 0.0))
        reasons = {str(k): str(v) for k, v in data.get("reasons", {}).items()} if isinstance(data.get("reasons"), dict) else {}
        return LayoutAIResponse(
            model=self._model,
            recommended=entries,
            reasons=reasons,
            raw_text=content,
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
