from __future__ import annotations

import json
import logging
import os
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


def resolve_template_path(*, spec: JobSpec, spec_source: Path) -> Path:
    """jobspec と spec ファイルからテンプレートパスの候補を解決する。"""

    template_path_value: str | None = None
    meta = getattr(spec, "meta", None)
    if meta is not None:
        template_path_value = getattr(meta, "template_path", None)
        if template_path_value is None and isinstance(meta, BaseModel):
            extra = getattr(meta, "model_extra", None)
            if isinstance(extra, dict):
                template_path_value = extra.get("template_path")
        if template_path_value is None and isinstance(meta, dict):
            template_path_value = meta.get("template_path")

    if not template_path_value:
        try:
            raw_spec = json.loads(spec_source.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            raw_spec = {}
        if isinstance(raw_spec, dict):
            template_path_value = raw_spec.get("meta", {}).get("template_path")  # type: ignore[assignment]

    if not template_path_value:
        raise ValueError("jobspec.meta.template_path にテンプレートパスを設定してください。")

    candidate_raw = Path(template_path_value)
    if candidate_raw.is_absolute():
        resolved = candidate_raw
    else:
        spec_relative = (spec_source.parent / candidate_raw).resolve()
        cwd_relative = (Path.cwd() / candidate_raw).resolve()
        if spec_relative.exists():
            resolved = spec_relative
        elif cwd_relative.exists():
            resolved = cwd_relative
        else:
            message = (
                "jobspec.meta.template_path にテンプレートパスを設定してください。"
                f"（確認したパス: {spec_relative}, {cwd_relative}）"
            )
            raise ValueError(message)

    if not resolved.exists():
        raise ValueError(f"テンプレートファイルが見つかりません: {resolved}")
    return resolved


def log_current_llm_provider(context: str) -> None:
    provider_env = os.getenv("PPTX_LLM_PROVIDER")
    provider = provider_env.strip().lower() if provider_env else "mock"
    source = "env" if provider_env else "default"
    logging.getLogger("pptx_generator.cli.llm").info(
        "LLM provider (%s): %s (source=%s)", context, provider, source
    )


def dump_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")
    logger.info("Saved JSON to %s", path.resolve())
