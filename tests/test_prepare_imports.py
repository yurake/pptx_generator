"""Ensure prepare AI aliases stay in sync with legacy modules."""

from __future__ import annotations

from importlib import import_module


def test_prepare_ai_aliases_prepare_modules() -> None:
    prepare_orch = import_module("pptx_generator.prepare.orchestrator")
    prepare_llm = import_module("pptx_generator.prepare.llm_client")
    prepare_prompts = import_module("pptx_generator.prepare.prompts")
    prepare_ai = import_module("pptx_generator.prepare_ai")

    assert prepare_ai.PrepareAIOrchestrator is prepare_orch.PrepareAIOrchestrator
    assert prepare_ai.create_prepare_llm_client is prepare_llm.create_prepare_llm_client
    assert prepare_ai.build_prepare_prompt_dynamic is prepare_prompts.build_prepare_prompt_dynamic


def test_prepare_wrappers_stay_in_sync() -> None:
    orchestrator = import_module("pptx_generator.prepare.orchestrator")
    llm_client = import_module("pptx_generator.prepare.llm_client")
    prompts = import_module("pptx_generator.prepare.prompts")
    prepare_ai = import_module("pptx_generator.prepare_ai")

    assert orchestrator.PrepareAIOrchestrator is prepare_ai.PrepareAIOrchestrator
    assert llm_client.create_prepare_llm_client is prepare_ai.create_prepare_llm_client
    assert prompts.build_prepare_prompt_dynamic is prepare_ai.build_prepare_prompt_dynamic
