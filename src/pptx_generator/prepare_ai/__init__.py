"""Prepare AI public interface."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from .errors import PrepareAIOrchestrationError
from .client import (
    AzureOpenAIPrepareLLMClient,
    MockPrepareLLMClient,
    OpenAIPrepareLLMClient,
    PrepareLLMClient,
    PrepareLLMConfigurationError,
    PrepareLLMResult,
    create_prepare_llm_client,
)
if TYPE_CHECKING:
    from .orchestrator import ALLOWED_STORY_PHASES, DEFAULT_PROMPT_ID, PrepareAIOrchestrator
    from .prompts import (
        PREPARE_DYNAMIC_PROMPT,
        PREPARE_STATIC_PROMPT,
        build_prepare_prompt_dynamic,
        build_prepare_prompt_static,
    )
    from .static_mode.types import StaticPromptOverride


def __getattr__(name: str):
    orchestrator_exports = {"ALLOWED_STORY_PHASES", "DEFAULT_PROMPT_ID", "PrepareAIOrchestrator"}
    prompt_exports = {
        "PREPARE_DYNAMIC_PROMPT",
        "PREPARE_STATIC_PROMPT",
        "build_prepare_prompt_dynamic",
        "build_prepare_prompt_static",
    }
    static_exports = {"StaticPromptOverride"}

    if name in orchestrator_exports:
        module = import_module(".orchestrator", __name__)
        return getattr(module, name)
    if name in prompt_exports:
        module = import_module(".prompts", __name__)
        return getattr(module, name)
    if name in static_exports:
        module = import_module(".static_mode.types", __name__)
        return getattr(module, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "ALLOWED_STORY_PHASES",
    "DEFAULT_PROMPT_ID",
    "PrepareAIOrchestrationError",
    "PrepareAIOrchestrator",
    "StaticPromptOverride",
    "AzureOpenAIPrepareLLMClient",
    "MockPrepareLLMClient",
    "OpenAIPrepareLLMClient",
    "PrepareLLMClient",
    "PrepareLLMConfigurationError",
    "PrepareLLMResult",
    "create_prepare_llm_client",
    "PREPARE_DYNAMIC_PROMPT",
    "PREPARE_STATIC_PROMPT",
    "build_prepare_prompt_dynamic",
    "build_prepare_prompt_static",
]
