"""LLM クライアントの生成を担当するファクトリ。"""

from __future__ import annotations

import logging
from typing import Callable

from ..llm import log_provider_resolution, resolve_llm_provider
from .clients import (
    AnthropicClaudeClient,
    AwsClaudeClient,
    AzureOpenAIChatClient,
    MockLLMClient,
    OpenAIChatClient,
)
from .errors import LLMClientConfigurationError
from .models import LLMClient

logger = logging.getLogger(__name__)


def create_llm_client() -> LLMClient:
    """環境変数に基づき LLM クライアントを生成する。"""

    resolution = resolve_llm_provider()
    log_provider_resolution(logging.getLogger("pptx_generator.slide_ai.llm"), component="slide_ai", resolution=resolution)

    factories: dict[str, Callable[[], LLMClient]] = {
        "mock": MockLLMClient,
        "openai": OpenAIChatClient.from_env,
        "azure-openai": AzureOpenAIChatClient.from_env,
        "anthropic": AnthropicClaudeClient.from_env,
        "aws-claude": AwsClaudeClient.from_env,
    }

    factory = factories.get(resolution.provider)
    if factory is None:
        msg = f"未知の LLM プロバイダーが指定されました: {resolution.provider}"
        raise LLMClientConfigurationError(msg)

    return factory()


__all__ = ["create_llm_client", "LLMClientConfigurationError"]
