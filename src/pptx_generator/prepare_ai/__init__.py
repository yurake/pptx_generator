"""Prepare AI components used by the Stage 2 pipeline."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Iterable, Sequence

_orchestrator = import_module("pptx_generator.prepare_ai.orchestrator")
_llm_client = import_module("pptx_generator.prepare_ai.llm_client")
_prompts = import_module("pptx_generator.prepare_ai.prompts")


def _collect_exports(module: Any) -> list[str]:
    names = getattr(module, "__all__", None)
    if names is None:
        names = [attr for attr in dir(module) if not attr.startswith("_")]
    return list(names)


def _export(module: Any, names: Sequence[str]) -> None:
    for name in names:
        globals()[name] = getattr(module, name)


_orchestrator_exports = _collect_exports(_orchestrator)
_llm_client_exports = _collect_exports(_llm_client)
_prompts_exports = _collect_exports(_prompts)

__all__ = sorted(set(_orchestrator_exports) | set(_llm_client_exports) | set(_prompts_exports))

_export(_orchestrator, _orchestrator_exports)
_export(_llm_client, _llm_client_exports)
_export(_prompts, _prompts_exports)
