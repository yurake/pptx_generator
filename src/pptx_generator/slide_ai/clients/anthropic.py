"""Anthropic Claude クライアント。"""

from __future__ import annotations

from ..constants import DEFAULT_MAX_TOKENS
from ..errors import LLMClientConfigurationError
from ..models import AIGenerationRequest, SlideMatchRequest
from ..prompt_builder import build_system_prompt, build_user_prompt
from ..response_parser import build_generation_response, build_slide_match_response
from ...llm import load_anthropic_config


class AnthropicClaudeClient:
    """Anthropic Claude API クライアント。"""

    def __init__(self, client, *, model: str, max_tokens: int, temperature: float) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature

    @classmethod
    def from_env(cls) -> "AnthropicClaudeClient":
        from anthropic import Anthropic

        config = load_anthropic_config(
            default_model="claude-3-haiku-20240307",
            default_temperature=0.3,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            error_cls=LLMClientConfigurationError,
        )
        client = Anthropic(api_key=config.api_key)
        return cls(client, model=config.model, max_tokens=config.max_tokens, temperature=config.temperature)

    def generate(self, request: AIGenerationRequest):
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
        model_name = request.policy.model or self._model
        if model_name == "mock-local":
            model_name = self._model
        response = self._client.messages.create(  # type: ignore[attr-defined]
            model=model_name,
            system=build_system_prompt(request),
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            messages=messages,
        )
        text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        text = "\n".join(text_parts)
        return build_generation_response(text, request, model=model_name)

    def match_slide(self, request: SlideMatchRequest):
        model_name = request.model or self._model
        if model_name == "mock-local":
            model_name = self._model
        response = self._client.messages.create(  # type: ignore[attr-defined]
            model=model_name,
            system=request.system_prompt,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": request.prompt,
                        }
                    ],
                }
            ],
        )
        text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        text = "\n".join(text_parts)
        return build_slide_match_response(text, request, model=model_name)


__all__ = ["AnthropicClaudeClient"]
