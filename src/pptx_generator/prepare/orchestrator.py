"""Compatibility wrapper for Prepare AI orchestrator."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_MODULE_PATH = "pptx_generator.prepare_ai.orchestrator"
_CACHED_MODULE: Any | None = None
__all__: list[str] = []


def _load_module() -> Any:
    global _CACHED_MODULE
    if _CACHED_MODULE is None:
        _CACHED_MODULE = import_module(_MODULE_PATH)
    return _CACHED_MODULE


def _ensure_all() -> list[str]:
    global __all__
    if not __all__:
        module = _load_module()
        names = getattr(module, "__all__", None)
        if names is None:
            names = [attr for attr in dir(module) if not attr.startswith("_")]
        __all__ = list(names)
    return __all__


def __getattr__(name: str) -> Any:
    module = _load_module()
    try:
        value = getattr(module, name)
    except AttributeError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals().keys()) | set(_ensure_all()))
