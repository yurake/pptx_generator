"""Prepare AI components used by the Stage 2 pipeline."""

from __future__ import annotations

from . import llm_client as _llm_client
from . import orchestrator as _orchestrator
from . import prompts as _prompts

__all__ = sorted(
    set(_orchestrator.__all__) | set(_llm_client.__all__) | set(_prompts.__all__)
)

globals().update({name: getattr(_orchestrator, name) for name in _orchestrator.__all__})
globals().update({name: getattr(_llm_client, name) for name in _llm_client.__all__})
globals().update({name: getattr(_prompts, name) for name in _prompts.__all__})
