"""Compatibility wrapper for prepare AI orchestrator."""

from __future__ import annotations

from pptx_generator.prepare_ai.errors import PrepareAIOrchestrationError
from pptx_generator.prepare_ai.orchestrator import DEFAULT_PROMPT_ID, PrepareAIOrchestrator

__all__ = [
    "DEFAULT_PROMPT_ID",
    "PrepareAIOrchestrationError",
    "PrepareAIOrchestrator",
]
