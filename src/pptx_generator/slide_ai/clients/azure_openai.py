"""Azure OpenAI Chat Completions クライアント。"""

from __future__ import annotations

from ..constants import DEFAULT_MAX_TOKENS
from ..errors import LLMClientConfigurationError
from ..models import AIGenerationRequest, SlideMatchRequest
from ..prompt_builder import build_system_prompt, build_user_prompt
from ..response_parser import build_generation_response, build_slide_match_response
from ...llm import load_azure_openai_config


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

    def _resolve_deployment(self, override: str | None) -> str:
        deployment = override if override and override.strip() else self._deployment
        return self._deployment if deployment == "mock-local" else deployment

    def _run_response(
        self,
        *,
        model_name: str,
        input_messages: list[dict[str, str]],
    ) -> tuple[str, str | None, str | None]:
        from openai.types.responses import ResponseOutputMessage
        from openai.types.responses.response_output_text import ResponseOutputText
        from openai.types.responses.response_output_refusal import ResponseOutputRefusal

        kwargs: dict[str, object] = {
            "model": model_name,
            "input": input_messages,
            "temperature": self._temperature,
        }
        if self._max_tokens > 0:
            kwargs["max_output_tokens"] = self._max_tokens
        response = self._client.responses.create(  # type: ignore[attr-defined]
            **kwargs,
        )

        text_segments: list[str] = []
        refusal_segments: list[str] = []
        for item in getattr(response, "output", []) or []:
            if isinstance(item, ResponseOutputMessage):
                for content in item.content:
                    if isinstance(content, ResponseOutputText):
                        text_segments.append(content.text)
                    elif isinstance(content, ResponseOutputRefusal):
                        refusal_segments.append(content.refusal)

        raw_text = "\n".join(segment.strip() for segment in text_segments if segment.strip())
        refusal_text = "\n".join(segment.strip() for segment in refusal_segments if segment.strip()) or None
        incomplete_details = getattr(response, "incomplete_details", None)
        finish_reason = None
        if incomplete_details is not None:
            finish_reason = getattr(incomplete_details, "reason", None) or "unknown"
        return raw_text, refusal_text, finish_reason

    @classmethod
    def from_env(cls) -> "AzureOpenAIChatClient":
        from openai import AzureOpenAI

        config = load_azure_openai_config(
            default_temperature=0.3,
            default_max_tokens=DEFAULT_MAX_TOKENS,
            default_api_version="2024-02-15-preview",
            error_cls=LLMClientConfigurationError,
        )
        client = AzureOpenAI(
            api_key=config.api_key,
            api_version=config.api_version,
            azure_endpoint=config.endpoint,
        )
        return cls(
            client,
            deployment=config.deployment,
            api_version=config.api_version,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

    def generate(self, request: AIGenerationRequest):
        messages = [
            {"role": "system", "content": build_system_prompt(request)},
            {"role": "user", "content": build_user_prompt(request)},
        ]
        deployment = self._resolve_deployment(request.policy.model)
        raw_text, refusal_text, finish_reason = self._run_response(
            model_name=deployment,
            input_messages=messages,
        )
        return build_generation_response(
            raw_text,
            request,
            model=deployment,
            finish_reason=finish_reason,
            refusal=refusal_text,
        )

    def match_slide(self, request: SlideMatchRequest):
        deployment = self._resolve_deployment(request.model)
        raw_text, refusal_text, finish_reason = self._run_response(
            model_name=deployment,
            input_messages=[
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.prompt},
            ],
        )
        return build_slide_match_response(
            raw_text,
            request,
            model=deployment,
            finish_reason=finish_reason,
            refusal=refusal_text,
        )


__all__ = ["AzureOpenAIChatClient"]
