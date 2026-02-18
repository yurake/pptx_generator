from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from pptx_generator.config import ConfigManager
from pptx_generator.logging import LOG_FORMAT, ensure_rotating_file_handler, ensure_stream_handler
from pptx_generator.models import JobSpec

logger = logging.getLogger(__name__)


LOG_LEVEL_ALIASES = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "warn": logging.WARNING,
    "error": logging.ERROR,
    "err": logging.ERROR,
    "fatal": logging.CRITICAL,
    "critical": logging.CRITICAL,
}

OUT_LOG_FILENAME = "out.log"


def _extract_meta_value(meta: object, key: str) -> str | None:
    if meta is None:
        return None

    direct_value = getattr(meta, key, None)
    if direct_value is not None:
        return direct_value

    if isinstance(meta, BaseModel):
        extra = getattr(meta, "model_extra", None)
        if isinstance(extra, dict):
            candidate = extra.get(key)
            if candidate is not None:
                return candidate

    if isinstance(meta, dict):
        return meta.get(key)

    return None


def _load_meta_value_from_file(spec_source: Path, key: str) -> str | None:
    try:
        raw_spec: dict[str, Any] = json.loads(spec_source.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None

    meta = raw_spec.get("meta")
    if not isinstance(meta, dict):
        return None

    value = meta.get(key)
    return value if value is not None else None


def _extract_path_from_config(
    config_manager: ConfigManager | None, key: str
) -> tuple[str | None, str | None]:
    if config_manager is None:
        return None, None

    candidate, source = config_manager.resolve_with_source(key)
    if isinstance(candidate, (str, Path)):
        return str(candidate), source

    return None, source


def _build_candidate_paths(path_value: str, spec_source: Path) -> list[Path]:
    candidate_raw = Path(path_value)
    if candidate_raw.is_absolute():
        return [candidate_raw]

    spec_relative = (spec_source.parent / candidate_raw).resolve()
    cwd_relative = (Path.cwd() / candidate_raw).resolve()
    return [spec_relative, cwd_relative]


def _normalize_path_value(value: object | None, *, key: str, allow_none: bool) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, Path)):
        return str(value)
    raise ValueError(f"jobspec.meta.{key} は文字列またはパスで指定してください。")


def parse_log_level(value: str | None) -> int | None:
    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    lowered = candidate.lower()
    if lowered in LOG_LEVEL_ALIASES:
        return LOG_LEVEL_ALIASES[lowered]
    try:
        numeric_level = int(candidate)
    except ValueError:
        return None
    return numeric_level


def determine_log_level(verbose: bool, debug: bool) -> tuple[int, list[tuple[int, str]]]:
    deferred_logs: list[tuple[int, str]] = []

    if debug:
        return logging.DEBUG, deferred_logs
    if verbose:
        return logging.INFO, deferred_logs

    env_level = os.getenv("LOG_LEVEL")
    parsed_level = parse_log_level(env_level)
    if env_level:
        if parsed_level is not None:
            return parsed_level, deferred_logs
        deferred_logs.append(
            (
                logging.WARNING,
                f"LOG_LEVEL='{env_level}' を解釈できません。WARNING レベルにフォールバックします。",
            )
        )

    return logging.WARNING, deferred_logs


def load_jobspec(path: Path) -> JobSpec:
    logger.info("Loading JobSpec from %s", path.resolve())
    return _load_jobspec_from_path(path)


def resolve_layouts_path(
    *,
    spec: JobSpec,
    spec_source: Path,
    config_manager: ConfigManager | None = None,
) -> Path | None:
    """jobspec と spec ファイルから layouts.jsonl の候補を解決する。"""

    layouts_path_value, source_name = _extract_path_from_config(config_manager, "layouts_path")
    if layouts_path_value is None:
        meta = getattr(spec, "meta", None)
        layouts_path_value = _extract_meta_value(meta, "layouts_path")
        if layouts_path_value is not None and source_name is None:
            source_name = "template_config"

    if layouts_path_value is None:
        layouts_path_value = _load_meta_value_from_file(spec_source, "layouts_path")
        if layouts_path_value is not None and source_name is None:
            source_name = "template_config"

    layouts_path_value = _normalize_path_value(layouts_path_value, key="layouts_path", allow_none=True)

    if not layouts_path_value:
        return None

    candidates = _build_candidate_paths(layouts_path_value, spec_source)

    for candidate in candidates:
        if candidate.exists():
            if config_manager is not None:
                config_manager.record("layouts_path", str(candidate), source_name)
            return candidate

    message = (
        "jobspec.meta.layouts_path に有効なパスを設定してください。"
        f"（確認したパス: {', '.join(str(path) for path in candidates)}）"
    )
    raise ValueError(message)


def resolve_template_path(
    *,
    spec: JobSpec,
    spec_source: Path,
    config_manager: ConfigManager | None = None,
) -> Path:
    """jobspec と spec ファイルからテンプレートパスの候補を解決する。"""

    template_path_value, source_name = _extract_path_from_config(config_manager, "template_path")

    if template_path_value is None:
        meta = getattr(spec, "meta", None)
        template_path_value = _extract_meta_value(meta, "template_path")
        if template_path_value is not None and source_name is None:
            source_name = "template_config"

    if template_path_value is None:
        template_path_value = _load_meta_value_from_file(spec_source, "template_path")
        if template_path_value is not None and source_name is None:
            source_name = "template_config"

    template_path_value = _normalize_path_value(template_path_value, key="template_path", allow_none=False)

    if not template_path_value:
        raise ValueError("jobspec.meta.template_path にテンプレートパスを設定してください。")

    candidates = _build_candidate_paths(template_path_value, spec_source)
    resolved = next((candidate for candidate in candidates if candidate.exists()), None)

    if resolved is None:
        message = (
            "jobspec.meta.template_path にテンプレートパスを設定してください。"
            f"（確認したパス: {', '.join(str(path) for path in candidates)}）"
        )
        raise ValueError(message)

    if not resolved.exists():
        raise ValueError(f"テンプレートファイルが見つかりません: {resolved}")

    if config_manager is not None:
        config_manager.record("template_path", str(resolved), source_name)
    return resolved


def log_current_llm_provider(context: str) -> None:
    logger.info("LLM provider resolved: component=%s provider=disabled source=local", context)



def configure_llm_logger(log_dir: Path | None = None) -> None:
    return


    target_dir = log_dir or Path("logs")
    target_dir.mkdir(parents=True, exist_ok=True)


def configure_file_logging(log_dir: Path | None = None) -> None:
    """`logs/out.log` へルートロガーの出力を複製するファイルハンドラを設定する。"""

    target_dir = log_dir or Path("logs")
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / OUT_LOG_FILENAME
    root_logger = logging.getLogger()
    formatter = logging.Formatter(LOG_FORMAT)
    ensure_stream_handler(
        root_logger,
        level=root_logger.getEffectiveLevel(),
        formatter=formatter,
        stream=sys.stdout,
    )
    ensure_rotating_file_handler(
        root_logger,
        file_path=file_path,
        level=root_logger.getEffectiveLevel(),
        formatter=formatter,
    )


def dump_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")
    logger.info("Saved JSON to %s", path.resolve())


def _load_jobspec_from_path(path: Path) -> JobSpec:
    raw = path.read_text(encoding="utf-8")
    try:
        return JobSpec.model_validate_json(raw)
    except Exception:
        pass

    from pptx_generator.models import JobSpecScaffold, JobMeta, JobAuth, Slide

    try:
        scaffold = JobSpecScaffold.model_validate_json(raw)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"jobspec の読み込みに失敗しました: {path}") from exc

    template_path = scaffold.meta.template_path
    template_id = scaffold.meta.template_id
    title = template_id or Path(template_path).stem

    meta = JobMeta(
        schema_version=scaffold.meta.schema_version,
        title=title,
        template_path=template_path,
        template_id=template_id,
        created_at=scaffold.meta.generated_at,
        layouts_path=scaffold.meta.layouts_path,
        template_spec_path=scaffold.meta.template_spec_path,
    )
    auth = JobAuth(created_by="cli")
    slides = []
    for slide in scaffold.slides:
        auto_draw = [p.anchor for p in slide.placeholders if p.auto_draw and p.anchor]
        slides.append(
            Slide(
                id=slide.id,
                layout=slide.layout,
                auto_draw_anchors=auto_draw,
            )
        )

    return JobSpec(meta=meta, auth=auth, slides=slides)
