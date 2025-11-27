"""Compatibility wrapper for Prepare AI orchestrator."""

from __future__ import annotations

from ..prepare_ai import orchestrator as _prepare_ai_orchestrator

__all__ = list(_prepare_ai_orchestrator.__all__)
__doc__ = _prepare_ai_orchestrator.__doc__

globals().update({name: getattr(_prepare_ai_orchestrator, name) for name in __all__})
