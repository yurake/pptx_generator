from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from .job_context import get_current_job


def get_transaction_id() -> str:
    current = get_current_job()
    if current and current.transaction_id:
        return current.transaction_id
    return uuid4().hex


def ensure_stage_output_dir(stage: str) -> Path:
    root = Path(os.getenv("PPTX_OUTPUT_ROOT", ".pptx")).resolve()
    tx_id = get_transaction_id()
    out_dir = root / tx_id / stage
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


__all__ = ["ensure_stage_output_dir", "get_transaction_id"]
