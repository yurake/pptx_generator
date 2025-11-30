from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from pptx_generator.models import JobSpec
from pptx_generator.spec_loader import load_jobspec_from_path

logger = logging.getLogger(__name__)


def load_jobspec(path: Path) -> JobSpec:
    logger.info("Loading JobSpec from %s", path.resolve())
    return load_jobspec_from_path(path)


def resolve_layouts_path(*, spec: JobSpec, spec_source: Path) -> Path | None:
    """jobspec と spec ファイルから layouts.jsonl の候補を解決する。"""

    layouts_path_value: str | None = None
    meta = getattr(spec, "meta", None)
    if meta is not None:
        layouts_path_value = getattr(meta, "layouts_path", None)
        if layouts_path_value is None and isinstance(meta, BaseModel):
            extra = getattr(meta, "model_extra", None)
            if isinstance(extra, dict):
                layouts_path_value = extra.get("layouts_path")
        if layouts_path_value is None and isinstance(meta, dict):
            layouts_path_value = meta.get("layouts_path")

    if layouts_path_value is None:
        try:
            raw_spec: dict[str, Any] = json.loads(spec_source.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            raw_spec = {}
        layouts_path_value = (
            raw_spec.get("meta", {}).get("layouts_path")
            if isinstance(raw_spec, dict)
            else None
        )

    if not layouts_path_value:
        return None

    candidate_raw = Path(layouts_path_value)
    if candidate_raw.is_absolute():
        candidates = [candidate_raw]
    else:
        spec_relative = (spec_source.parent / candidate_raw).resolve()
        cwd_relative = (Path.cwd() / candidate_raw).resolve()
        candidates = [spec_relative, cwd_relative]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    message = (
        "jobspec.meta.layouts_path に有効なパスを設定してください。"
        f"（確認したパス: {', '.join(str(path) for path in candidates)}）"
    )
    raise ValueError(message)
def dump_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")
    logger.info("Saved JSON to %s", path.resolve())

