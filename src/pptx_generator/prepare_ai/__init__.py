"""Prepare AI components used by the Stage 2 pipeline."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Iterable

_MODULE_PATHS = (
    "pptx_generator.prepare_ai.orchestrator",
    "pptx_generator.prepare_ai.llm_client",
    "pptx_generator.prepare_ai.prompts",
)

_CACHED_MODULES: list[Any | None] = [None, None, None]
__all__: list[str] = []


def _iterate_modules() -> Iterable[Any]:
    for index, path in enumerate(_MODULE_PATHS):
        module = _CACHED_MODULES[index]
        if module is None:
            module = import_module(path)
            _CACHED_MODULES[index] = module
        yield module


def _ensure_all() -> list[str]:
    global __all__
    if not __all__:
        names: set[str] = set()
        for module in _iterate_modules():
            module_all = getattr(module, "__all__", None)
            if module_all is None:
                module_all = [attr for attr in dir(module) if not attr.startswith("_")]
            names.update(module_all)
        __all__ = sorted(names)
    return __all__


def __getattr__(name: str) -> Any:
    for module in _iterate_modules():
        if hasattr(module, name):
            value = getattr(module, name)
            globals()[name] = value
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals().keys()) | set(_ensure_all()))
