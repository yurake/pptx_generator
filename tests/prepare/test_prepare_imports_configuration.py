"""Ensure prepare AI modules expose canonical entry points."""

from __future__ import annotations

from importlib import import_module

import pytest


def test_prepare_ai_exports_match_submodules() -> None:
    prepare_ai = import_module("pptx_generator.prepare_ai")
    orchestrator = import_module("pptx_generator.prepare.orchestrator")
    client_module = import_module("pptx_generator.prepare_ai.client")
    prompts = import_module("pptx_generator.prepare_ai.prompts")

    assert prepare_ai.PrepareAIOrchestrator is orchestrator.PrepareAIOrchestrator
    assert prepare_ai.create_prepare_llm_client is client_module.create_prepare_llm_client
    assert prepare_ai.build_prepare_prompt_dynamic is prompts.build_prepare_prompt_dynamic


def test_legacy_prepare_modules_removed() -> None:
    with pytest.raises(ModuleNotFoundError):
        import_module("pptx_generator.prepare.client")
    with pytest.raises(ModuleNotFoundError):
        import_module("pptx_generator.prepare.prompts")
