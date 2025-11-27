"""Compatibility wrapper for Prepare AI prompt helpers."""

from __future__ import annotations

from ..prepare_ai import prompts as _prepare_ai_prompts

__all__ = list(_prepare_ai_prompts.__all__)
__doc__ = _prepare_ai_prompts.__doc__

globals().update({name: getattr(_prepare_ai_prompts, name) for name in __all__})
