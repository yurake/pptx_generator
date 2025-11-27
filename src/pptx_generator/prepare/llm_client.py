"""Compatibility wrapper for Prepare AI LLM client."""

from __future__ import annotations

from ..prepare_ai import llm_client as _prepare_ai_llm_client

__all__ = list(_prepare_ai_llm_client.__all__)
__doc__ = _prepare_ai_llm_client.__doc__

globals().update({name: getattr(_prepare_ai_llm_client, name) for name in __all__})
