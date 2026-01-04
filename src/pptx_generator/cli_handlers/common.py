from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from pptx_generator.config_manager import ConfigManager
from pptx_generator.llm import log_provider_resolution, resolve_llm_provider
from pptx_generator.logging import LOG_FORMAT, ensure_rotating_file_handler, ensure_stream_handler
from pptx_generator.models import JobSpec
from pptx_generator.spec_loader import load_jobspec_from_path

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
    return str(value) if value is not None else None


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
    return load_jobspec_from_path(path)


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
    resolution = resolve_llm_provider()
    log_provider_resolution(
        logging.getLogger("pptx_generator.cli.llm"),
        component=context,
        resolution=resolution,
    )


def configure_llm_logger(log_dir: Path | None = None) -> None:
    """LLM ログのファイル・ストリーム出力を準備する。"""

    target_dir = log_dir or Path("logs")
    target_dir.mkdir(parents=True, exist_ok=True)
    llm_logger = logging.getLogger("pptx_generator.slide_ai.llm")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    class _LLMLogFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return True

    if not any(isinstance(f, _LLMLogFilter) for f in llm_logger.filters):
        llm_logger.addFilter(_LLMLogFilter())

    existing_handler = next(
        (
            handler
            for handler in llm_logger.handlers
            if isinstance(handler, logging.FileHandler)
            and getattr(handler, "baseFilename", None) == str(target_dir / OUT_LOG_FILENAME)
        ),
        None,
    )
    if existing_handler:
        existing_handler.setLevel(logging.INFO)
        existing_handler.setFormatter(formatter)
    else:
        ensure_rotating_file_handler(
            llm_logger,
            file_path=target_dir / OUT_LOG_FILENAME,
            level=logging.INFO,
            formatter=formatter,
        )

    stream_handler_exists = any(
        isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
        for handler in llm_logger.handlers
    )
    if not stream_handler_exists:
        ensure_stream_handler(
            llm_logger,
            level=logging.INFO,
            formatter=formatter,
            stream=sys.stdout,
        )
    llm_logger.setLevel(logging.INFO)
    llm_logger.propagate = False


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
