"""Ensure prepare AI packages and compatibility wrappers initialize safely."""

from __future__ import annotations

import importlib
import sys


def _fresh_import(name: str, extra: tuple[str, ...] = ()) -> object:
    """Import a module after removing it (and optionally its parents) from sys.modules."""
    for mod_name in (name, *extra):
        sys.modules.pop(mod_name, None)
    return importlib.import_module(name)


def test_prepare_ai_exports_available() -> None:
    module = _fresh_import(
        "pptx_generator.prepare_ai",
        extra=(
            "pptx_generator.prepare_ai.orchestrator",
            "pptx_generator.prepare_ai.llm_client",
            "pptx_generator.prepare_ai.prompts",
        ),
    )

    for attr in (
        "PrepareAIOrchestrator",
        "create_prepare_llm_client",
        "build_prepare_prompt_dynamic",
    ):
        assert hasattr(module, attr), f"{attr} should be exported from prepare_ai"
        assert attr in module.__dir__()


def test_prepare_orchestrator_wrapper_deferred_exports() -> None:
    importlib.import_module("pptx_generator.prepare_ai")
    compat = _fresh_import(
        "pptx_generator.prepare.orchestrator",
        extra=("pptx_generator.prepare",),
    )
    target = importlib.import_module("pptx_generator.prepare_ai.orchestrator")

    assert compat.__getattr__("PrepareAIOrchestrator") is target.PrepareAIOrchestrator
    assert "PrepareAIOrchestrator" in compat.__dir__()


def test_prepare_llm_client_wrapper_deferred_exports() -> None:
    importlib.import_module("pptx_generator.prepare_ai")
    compat = _fresh_import(
        "pptx_generator.prepare.llm_client",
        extra=("pptx_generator.prepare",),
    )
    target = importlib.import_module("pptx_generator.prepare_ai.llm_client")

    assert compat.__getattr__("create_prepare_llm_client") is target.create_prepare_llm_client
    assert "create_prepare_llm_client" in compat.__dir__()


def test_prepare_prompts_wrapper_deferred_exports() -> None:
    importlib.import_module("pptx_generator.prepare_ai")
    compat = _fresh_import(
        "pptx_generator.prepare.prompts",
        extra=("pptx_generator.prepare",),
    )
    target = importlib.import_module("pptx_generator.prepare_ai.prompts")

    assert compat.__getattr__("build_prepare_prompt_dynamic") is target.build_prepare_prompt_dynamic
    assert "build_prepare_prompt_dynamic" in compat.__dir__()
