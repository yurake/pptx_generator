from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass(slots=True)
class PrepareCommandConfig:
    prepare_path: Path | None
    prepare_inputs: Sequence[str]
    output_dir: Path
    jobspec_path: Path | None
    mode: str
    page_limit: int | None
    default_jobspec_path: Path
    prompts_dirname: Path
    slide_inputs_filename: Path


@dataclass(slots=True)
class PrepareCommandResult:
    messages: list[str]
    cards_path: Path
    log_path: Path
    ai_log_path: Path
    meta_path: Path
    story_outline_path: Path
    audit_path: Path


@dataclass(slots=True)
class PrepareStaticContext:
    blueprint_spec: Any | None
    blueprint_ref: Any | None
    template_spec_path: Path | None
    prompt_overrides: list[Any]
    slide_input_sources: Any | None
    slide_input_refs: Any | None
    source_document: Any | None
    messages: list[str]
    import_metadata: list[dict[str, Any]]
