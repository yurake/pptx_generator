"""Compatibility wrapper for prepare AI prompts."""

from __future__ import annotations

from pptx_generator.prepare_ai.prompts import (
    PREPARE_DYNAMIC_PROMPT,
    PREPARE_STATIC_PROMPT,
    build_prepare_prompt_dynamic,
    build_prepare_prompt_static,
)

__all__ = [
    "PREPARE_DYNAMIC_PROMPT",
    "PREPARE_STATIC_PROMPT",
    "build_prepare_prompt_dynamic",
    "build_prepare_prompt_static",
]
