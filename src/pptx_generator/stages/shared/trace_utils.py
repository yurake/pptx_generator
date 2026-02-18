from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pptx_generator.pipeline import PipelineContext, write_pipeline_trace

_STAGE_DIR_NAMES = {"template", "prepare", "compose", "gen"}


def _read_trace_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [entry for entry in data if isinstance(entry, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def resolve_trace_root(output_dir: Path) -> Path:
    """ステージ配下のディレクトリ構造を前提に trace のルートを決める."""
    if output_dir.name in _STAGE_DIR_NAMES:
        return output_dir.parent
    return output_dir


def inherit_transaction_id(trace_root: Path, default: str) -> str:
    entries = _read_trace_entries(trace_root / "pipeline_trace.json")
    if not entries:
        return default
    last = entries[-1]
    return str(last.get("transaction_id") or default)


def record_stage_trace(
    *,
    context: PipelineContext,
    stage: str,
    output_dir: Path,
) -> Path:
    trace_root = resolve_trace_root(output_dir)
    context.transaction_id = inherit_transaction_id(trace_root, context.transaction_id)

    stage_trace_path = write_pipeline_trace(context, output_dir)

    root_trace_path = trace_root / "pipeline_trace.json"
    entries = _read_trace_entries(root_trace_path)
    entries.append(
        {
            "stage": stage,
            "job_id": context.job_id,
            "transaction_id": context.transaction_id,
            "workdir": str(output_dir),
            "pipeline_trace_path": str(stage_trace_path),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    root_trace_path.parent.mkdir(parents=True, exist_ok=True)
    root_trace_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    return root_trace_path
