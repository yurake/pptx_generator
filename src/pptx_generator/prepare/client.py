"""Compatibility wrapper for prepare AI client module."""

from __future__ import annotations

from pptx_generator.prepare_ai.client import (
    AzureOpenAIPrepareLLMClient,
    MockPrepareLLMClient,
    OpenAIPrepareLLMClient,
    PrepareLLMClient,
    PrepareLLMConfigurationError,
    PrepareLLMResult,
    create_prepare_llm_client,
)

__all__ = [
    "AzureOpenAIPrepareLLMClient",
    "MockPrepareLLMClient",
    "OpenAIPrepareLLMClient",
    "PrepareLLMClient",
    "PrepareLLMConfigurationError",
    "PrepareLLMResult",
    "create_prepare_llm_client",
]
