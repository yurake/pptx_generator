from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from pptx_generator.prepare import PrepareCard, PrepareDocument
from pptx_generator.prepare.models import PrepareGenerationMeta
from pptx_generator.prepare_ai import StaticPromptOverride
from pptx_generator.models import TemplateSpec
from pptx_generator.prepare.source import PrepareSourceDocument


@dataclass(slots=True)
class PrepareCommandConfig:
    prepare_path: Path | None
    prepare_inputs: tuple[str, ...]
    output_dir: Path
    jobspec_path: Path | None
    mode: str
    page_limit: int | None
    default_jobspec_path: Path
    prompts_dirname: Path
    slide_inputs_filename: Path


@dataclass(slots=True)
class PrepareCommandResult:
    cards_path: Path
    log_path: Path
    ai_log_path: Path
    meta_path: Path
    story_outline_path: Path
    audit_path: Path
    messages: list[str]


@dataclass(slots=True)
class PrepareStaticContext:
    blueprint_spec: TemplateSpec | None
    blueprint_ref: dict[str, str] | None
    template_spec_path: Path | None
    prompt_overrides: list[StaticPromptOverride]
    slide_input_sources: dict[str, PrepareSourceDocument] | None
    slide_input_refs: dict[str, str] | None
    source_document: PrepareSourceDocument | None
    messages: list[str]
    import_metadata: list[dict[str, Any]]
