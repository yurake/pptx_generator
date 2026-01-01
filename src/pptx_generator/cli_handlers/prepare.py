from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Sequence

from pptx_generator.models import JobAuth, JobMeta, JobSpec
from pptx_generator.pipeline import PipelineContext, PipelineStage
from pptx_generator.cli_handlers.trace_utils import record_stage_trace
from pptx_generator.prepare.source import PrepareSourceDocument
from pptx_generator.prepare_ai import PrepareAIOrchestrationError, PrepareAIOrchestrator

from .prepare_artifacts import PrepareCommandArtifacts
from .prepare_errors import PrepareCommandError
from .prepare_inputs import load_prepare_inputs as _load_prepare_inputs
from .prepare_inputs import load_prepare_input as _load_prepare_input
from .prepare_models import PrepareCommandConfig, PrepareCommandResult, PrepareStaticContext
from .prepare_static import (
    PROMPT_DEFAULT_LINES,
    PROMPT_TEMPLATE_FILENAME_PATTERN,
    PROMPT_USER_SECTION_END,
    PROMPT_USER_SECTION_START,
    build_prompt_identifier,
    load_prompt_overrides,
    resolve_static_context,
    slugify_prompt_layout,
)

logger = logging.getLogger(__name__)

SLIDE_INPUTS_FILENAME = Path("slide_inputs.md")


def run_prepare_command(
    config: PrepareCommandConfig,
    *,
    dump_json: Callable[[Path, object], None],
) -> PrepareCommandResult:
    normalized_mode = config.mode.lower()
    if normalized_mode not in {"dynamic", "static"}:
        raise PrepareCommandError("--mode には dynamic か static を指定してください", exit_code=2)
    if normalized_mode == "static" and config.page_limit is not None:
        raise PrepareCommandError("static モードでは --page-limit を利用できません", exit_code=2)

    source_document, inline_metadata, import_messages = _resolve_inputs(config.prepare_inputs)
    static_context = resolve_static_context(
        jobspec_path=config.jobspec_path,
        default_jobspec_path=config.default_jobspec_path,
        prompts_dirname=config.prompts_dirname,
        slide_inputs_filename=config.slide_inputs_filename,
        mode=normalized_mode,
        prepare_path=config.prepare_path,
        has_inline_source=source_document is not None,
    )

    source_document, source_metadata = _select_source_document(
        inline_document=source_document,
        inline_metadata=inline_metadata,
        static_context=static_context,
        prepare_path=config.prepare_path,
    )

    orchestrator = PrepareAIOrchestrator()
    try:
        document, meta, ai_logs = orchestrator.generate_document(
            source_document,
            page_limit=config.page_limit,
            mode=normalized_mode,  # type: ignore[arg-type]
            blueprint=static_context.blueprint_spec.blueprint if static_context.blueprint_spec else None,
            blueprint_ref=static_context.blueprint_ref,
            prompt_overrides=static_context.prompt_overrides,
            slide_sources=static_context.slide_input_sources,
            slide_input_refs=static_context.slide_input_refs,
        )
    except PrepareAIOrchestrationError as exc:
        exit_code = 6 if normalized_mode == "static" else 4
        raise PrepareCommandError(f"プレペアカードの生成に失敗しました: {exc}", exit_code=exit_code) from exc

    if source_metadata:
        meta.import_sources = source_metadata

    artifacts = PrepareCommandArtifacts.initialize(config.output_dir)
    combined_messages = [*import_messages, *static_context.messages]
    result = artifacts.write_outputs(
        document=document,
        meta=meta,
        ai_logs=ai_logs,
        dump_json=dump_json,
        static_context=static_context,
        messages=combined_messages,
        import_metadata=source_metadata,
    )
    _record_prepare_trace(config.output_dir)
    return result


def _resolve_inputs(
    prepare_inputs: Sequence[str],
) -> tuple[PrepareSourceDocument | None, list[dict[str, Any]], list[str]]:
    source_document: PrepareSourceDocument | None = None
    metadata: list[dict[str, Any]] = []
    messages: list[str] = []
    if prepare_inputs:
        source_document, metadata, messages = _load_prepare_inputs(prepare_inputs)
        if messages:
            logger.info("prepare inputs loaded: %s", "; ".join(messages))
    return source_document, metadata, messages


def _select_source_document(
    *,
    inline_document: PrepareSourceDocument | None,
    inline_metadata: list[dict[str, Any]],
    static_context: PrepareStaticContext,
    prepare_path: Path | None,
) -> tuple[PrepareSourceDocument | None, list[dict[str, Any]]]:
    source_document = inline_document
    source_metadata: list[dict[str, Any]] = list(inline_metadata)

    if static_context.import_metadata:
        source_metadata.extend(static_context.import_metadata)

    if source_document is None and static_context.source_document is not None:
        source_document = static_context.source_document
        if static_context.template_spec_path is not None:
            source_metadata.append(
                {
                    "source": str(static_context.template_spec_path),
                    "kind": "template_spec",
                    "retrieved_at": _now_iso(),
                }
            )

    if source_document is None and prepare_path is not None:
        from pptx_generator.prepare.source import PrepareSourceDocument

        source_document = _load_prepare_source(prepare_path)
        source_metadata.append(
            _build_structured_source_meta(prepare_path, source_document)
        )

    if source_document is None and static_context.slide_input_sources:
        source_document = next(iter(static_context.slide_input_sources.values()))

    if source_document is None:
        raise PrepareCommandError(
            "dynamic モードではプレペア入力を指定する必要があります",
            exit_code=2,
        )

    return source_document, source_metadata


def _load_prepare_source(path: Path) -> PrepareSourceDocument:
    from pptx_generator.prepare.source import PrepareSourceDocument
    from pydantic import ValidationError
    import json

    try:
        return PrepareSourceDocument.parse_file(path)
    except FileNotFoundError as exc:
        raise PrepareCommandError(f"プレペア入力ファイルが見つかりません: {exc}", exit_code=2) from exc
    except (json.JSONDecodeError, ValidationError) as exc:
        raise PrepareCommandError(f"プレペア入力の解析に失敗しました: {exc}", exit_code=2) from exc
    except UnicodeDecodeError as exc:
        raise PrepareCommandError(f"プレペア入力ファイルを UTF-8 として解釈できません: {exc}", exit_code=2) from exc


def _build_structured_source_meta(path: Path, document: PrepareSourceDocument) -> dict[str, Any]:
    import hashlib
    from .prepare_inputs import _guess_structured_content_type

    try:
        raw_bytes = path.read_bytes()
    except OSError:
        raw_bytes = b""
    hash_value = hashlib.sha256(raw_bytes).hexdigest() if raw_bytes else None
    metadata = {
        "source": str(path),
        "kind": "file",
        "retrieved_at": _now_iso(),
        "hash": f"sha256:{hash_value}" if hash_value else None,
        "chapters": len(getattr(document, "chapters", []) or []),
        "content_type": _guess_structured_content_type(path.suffix.lower()),
        "via": "structured",
    }
    return {key: value for key, value in metadata.items() if value is not None}


def _record_prepare_trace(output_dir: Path) -> None:
    stub_spec = JobSpec(
        meta=JobMeta(schema_version="1.0", title="prepare"),
        auth=JobAuth(created_by="cli"),
        slides=[],
    )
    context = PipelineContext(spec=stub_spec, workdir=output_dir)
    context.current_stage = PipelineStage.PREPARE
    record_stage_trace(context=context, stage="prepare", output_dir=output_dir)


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


_resolve_static_context = resolve_static_context
_load_prompt_overrides = load_prompt_overrides

__all__ = [
    "PROMPT_DEFAULT_LINES",
    "PROMPT_TEMPLATE_FILENAME_PATTERN",
    "PROMPT_USER_SECTION_END",
    "PROMPT_USER_SECTION_START",
    "SLIDE_INPUTS_FILENAME",
    "PrepareCommandConfig",
    "PrepareCommandError",
    "PrepareCommandResult",
    "PrepareCommandArtifacts",
    "PrepareStaticContext",
    "load_prompt_overrides",
    "_load_prompt_overrides",
    "resolve_static_context",
    "_resolve_static_context",
    "build_prompt_identifier",
    "run_prepare_command",
    "slugify_prompt_layout",
    "_load_prepare_inputs",
    "_load_prepare_input",
]
