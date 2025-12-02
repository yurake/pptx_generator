"""成果物ファイルの書き出し。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ...models import (
    GenerateReadyDocument,
    GenerateReadyMeta,
    MappingLog,
)
from .types import MappingAccumulator, MappingOptions
from ..base import PipelineContext


def finalize_outputs(
    *,
    context: PipelineContext,
    options: MappingOptions,
    output_dir: Path,
    generate_ready_document: GenerateReadyDocument,
    mapping_log: MappingLog,
    accumulator: MappingAccumulator,
    template_path_str: str | None,
    generate_ready_meta: GenerateReadyMeta,
    elapsed_ms: int,
) -> None:
    generate_ready_path = output_dir / options.generate_ready_filename
    generate_ready_path.write_text(
        json.dumps(
            generate_ready_document.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    mapping_log_path = output_dir / options.mapping_log_filename
    mapping_log_path.write_text(
        json.dumps(
            mapping_log.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if accumulator.fallback_records and options.fallback_report_filename:
        fallback_path = output_dir / options.fallback_report_filename
        fallback_path.write_text(
            json.dumps(
                {
                    "generated_at": generate_ready_meta.generated_at,
                    "slides": accumulator.fallback_records,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        context.add_artifact("mapping_fallback_report_path", str(fallback_path))

    context.add_artifact("generate_ready", generate_ready_document)
    context.add_artifact("generate_ready_path", str(generate_ready_path))
    context.add_artifact("mapping_log", mapping_log)
    context.add_artifact("mapping_log_path", str(mapping_log_path))

    mapping_meta = _build_mapping_meta(
        accumulator=accumulator,
        generate_ready_meta=generate_ready_meta,
        template_path_str=template_path_str,
        generate_ready_path=generate_ready_path,
        elapsed_ms=elapsed_ms,
    )
    context.add_artifact("mapping_meta", mapping_meta)


def _build_mapping_meta(
    *,
    accumulator: MappingAccumulator,
    generate_ready_meta: GenerateReadyMeta,
    template_path_str: str | None,
    generate_ready_path: Path,
    elapsed_ms: int,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "elapsed_ms": elapsed_ms,
        "slides": len(accumulator.generate_ready_slides),
        "fallback_count": len(accumulator.fallback_slide_ids),
        "fallback_slide_ids": sorted(accumulator.fallback_slide_ids),
        "ai_patch_count": accumulator.ai_patch_count,
        "ai_patch_slide_ids": sorted(accumulator.ai_patch_slide_ids),
        "generate_ready_generated_at": generate_ready_meta.generated_at,
        "template_version": generate_ready_meta.template_version,
        "content_hash": generate_ready_meta.content_hash,
        "generate_ready_path": str(generate_ready_path),
    }
    if template_path_str is not None:
        meta["template_path"] = template_path_str
    return meta


def format_template_path(template_path: Path, output_dir: Path) -> str:
    try:
        relative = template_path.relative_to(output_dir)
        return str(relative)
    except ValueError:
        try:
            return os.path.relpath(template_path, output_dir)
        except ValueError:
            return str(template_path)


def resolve_template_version(
    *,
    context: PipelineContext,
    options: MappingOptions,
) -> str | None:
    style_artifact = context.artifacts.get("template_style")
    if isinstance(style_artifact, dict):
        source = style_artifact.get("source")
        if isinstance(source, dict):
            template = source.get("template")
            if isinstance(template, str):
                return Path(template).stem
    if options.template_path is not None:
        return options.template_path.stem
    return None


def resolve_content_hash(context: PipelineContext) -> str | None:
    meta = context.artifacts.get("content_approved_meta")
    if isinstance(meta, dict):
        hash_value = meta.get("hash")
        if isinstance(hash_value, str):
            return hash_value
    return None
