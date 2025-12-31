"""OpenAI Chat Completions クライアント。"""

from __future__ import annotations

import json
import time

from ..constants import DEFAULT_MAX_TOKENS
from ..errors import LLMClientConfigurationError
from ..loggers import LLM_LOGGER
from ..models import AIGenerationRequest, AIGenerationResponse, SlideMatchRequest, SlideMatchResponse
from ..prompt_builder import build_system_prompt, build_user_prompt
from ..response_parser import build_generation_response, build_slide_match_response
from ...llm import load_openai_chat_config
from ...llm import log_provider_resolution, resolve_llm_provider  # re-export convenience


class OpenAIChatClient:
    """OpenAI Chat Completions API クライアント。"""

    def __init__(self, client, *, model: str, temperature: float, max_tokens: int) -> None:
        self._client = client
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    def _resolve_model_name(self, override: str | None) -> str:
        model_name = override if override and override.strip() else self._model
        return self._model if model_name == "mock-local" else model_name

    def _chat_completion(
        self,
        *,
        messages: list[dict[str, str]],
        model_name: str,
    ) -> tuple[str, str | None, str | None]:
        kwargs: dict[str, object] = {
            "model": model_name,
            "messages": messages,
            "temperature": self._temperature,
            "response_format": {"type": "json_object"},
        }
        if self._max_tokens > 0:
            kwargs["max_completion_tokens"] = self._max_tokens
        response = self._client.chat.completions.create(  # type: ignore[attr-defined]
            **kwargs,
        )
        choice = response.choices[0]  # type: ignore[index]
        message = choice.message
        content = getattr(message, "content", None)
        if isinstance(content, str):
            text = content
        elif content is None:
            text = ""
        elif isinstance(content, (list, tuple)):
            segments: list[str] = []
            for part in content:
                if isinstance(part, str):
                    segments.append(part)
                elif isinstance(part, dict):
                    segments.append(json.dumps(part, ensure_ascii=False))
                else:
                    segments.append(str(part))
            text = "".join(segments)
        else:
            text = str(content)
        return text, getattr(choice, "finish_reason", None), getattr(message, "refusal", None)

    @classmethod
    def from_env(cls) -> "OpenAIChatClient":
        from openai import OpenAI

        config = load_openai_chat_config(
            default_model="gpt-5-mini",
            default_temperature=0.3,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            error_cls=LLMClientConfigurationError,
        )
        client = OpenAI(api_key=config.api_key, base_url=config.base_url) if config.base_url else OpenAI(api_key=config.api_key)
        return cls(client, model=config.model, temperature=config.temperature, max_tokens=config.max_tokens)

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        messages = [
            {"role": "system", "content": build_system_prompt(request)},
            {"role": "user", "content": build_user_prompt(request)},
        ]
        model_name = self._resolve_model_name(request.policy.model)
        start = time.perf_counter()
        LLM_LOGGER.info(
            "slide_ai call start model=%s slide_id=%s",
            model_name,
            request.slide.id,
        )
        try:
            text, finish_reason, refusal = self._chat_completion(
                messages=messages,
                model_name=model_name,
            )
        except Exception as exc:  # noqa: BLE001
            LLM_LOGGER.error(
                "OpenAI chat completion error: %s",
                exc,
                extra={
                    "model": model_name,
                    "slide_id": request.slide.id,
                },
            )
            raise RuntimeError("OpenAI API call failed") from exc
        latency_ms = (time.perf_counter() - start) * 1000
        result = build_generation_response(
            text,
            request,
            model=model_name,
            finish_reason=finish_reason,
            refusal=refusal,
        )
        LLM_LOGGER.info(
            "slide_ai call done model=%s slide_id=%s latency_ms=%.1f finish_reason=%s",
            model_name,
            request.slide.id,
            latency_ms,
            finish_reason,
        )
        return result

    def match_slide(self, request: SlideMatchRequest) -> SlideMatchResponse:
        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.prompt},
        ]
        model_name = self._resolve_model_name(request.model)
        try:
            text, finish_reason, refusal = self._chat_completion(
                messages=messages,
                model_name=model_name,
            )
        except Exception as exc:  # noqa: BLE001
            LLM_LOGGER.error(
                "OpenAI chat completion error: %s",
                exc,
                extra={
                    "model": model_name,
                    "card_id": request.card_id,
                },
            )
            raise RuntimeError("OpenAI API match call failed") from exc
        return build_slide_match_response(
            text,
            request,
            model=model_name,
            finish_reason=finish_reason,
            refusal=refusal,
        )


__all__ = ["OpenAIChatClient", "log_provider_resolution", "resolve_llm_provider"]
