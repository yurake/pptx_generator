"""Compatibility wrapper for prepare AI LLM client."""

from __future__ import annotations

from pptx_generator.prepare_ai.llm_client import (
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
