"""Compatibility wrapper for Prepare AI prompt helpers."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_prepare_ai_prompts = import_module("pptx_generator.prepare_ai.prompts")


def _resolve_exports(module: Any) -> list[str]:
    names = getattr(module, "__all__", None)
    if names is None:
        names = [attr for attr in dir(module) if not attr.startswith("_")]
    return list(names)


def __getattr__(name: str) -> Any:
    return getattr(_prepare_ai_prompts, name)


def __dir__() -> list[str]:
    return _resolve_exports(_prepare_ai_prompts)


__all__ = __dir__()
__doc__ = getattr(_prepare_ai_prompts, "__doc__", __doc__)

globals().update({name: getattr(_prepare_ai_prompts, name) for name in __all__})
