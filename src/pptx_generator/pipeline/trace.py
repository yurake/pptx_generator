from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import PipelineContext, StageResult
from ..config import ResolvedConfig


def _serialize_stage_result(result: StageResult) -> dict[str, Any]:
    return {
        "stage": result.stage.value,
        "success": result.success,
        "details": result.details,
    }


def _serialize_config_snapshot(snapshot: ResolvedConfig | None) -> dict[str, Any] | None:
    if snapshot is None:
        return None
    return {
        "values": snapshot.values,
        "sources": snapshot.sources,
        "priority_order": list(snapshot.priority_order),
    }


def write_pipeline_trace(
    context: PipelineContext,
    output_dir: Path,
    filename: str = "pipeline_trace.json",
) -> Path:
    """PipelineContext のトレース情報を JSON へ書き出す。"""

    payload = {
        "job_id": context.job_id,
        "transaction_id": context.transaction_id,
        "current_stage": context.current_stage.value if context.current_stage else None,
        "execution_trace": list(context.execution_trace),
        "stage_results": [_serialize_stage_result(result) for result in context.stage_results],
        "error_history": list(context.error_history),
        "config_snapshot": _serialize_config_snapshot(context.config_snapshot),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    context.add_artifact("pipeline_trace_path", str(path))
    return path


__all__ = ["write_pipeline_trace"]
