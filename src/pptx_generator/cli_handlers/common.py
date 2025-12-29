from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from logging.handlers import RotatingFileHandler
from pydantic import BaseModel

from pptx_generator.config_manager import ConfigManager
from pptx_generator.llm import log_provider_resolution, resolve_llm_provider
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

    source_name: str | None = None
    layouts_path_value: str | None = None
    if config_manager is not None:
        candidate, resolved_source = config_manager.resolve_with_source("layouts_path")
        if isinstance(candidate, (str, Path)):
            layouts_path_value = str(candidate)
            source_name = resolved_source

    meta = getattr(spec, "meta", None)
    if layouts_path_value is None and meta is not None:
        layouts_path_value = getattr(meta, "layouts_path", None)
        if layouts_path_value is None and isinstance(meta, BaseModel):
            extra = getattr(meta, "model_extra", None)
            if isinstance(extra, dict):
                layouts_path_value = extra.get("layouts_path")
        if layouts_path_value is None and isinstance(meta, dict):
            layouts_path_value = meta.get("layouts_path")
        if layouts_path_value is not None and source_name is None:
            source_name = "template_config"

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
        if layouts_path_value is not None and source_name is None:
            source_name = "template_config"

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

    template_path_value: str | None = None
    source_name: str | None = None

    if config_manager is not None:
        candidate, resolved_source = config_manager.resolve_with_source("template_path")
        if isinstance(candidate, (str, Path)):
            template_path_value = str(candidate)
            source_name = resolved_source

    meta = getattr(spec, "meta", None)
    if template_path_value is None and meta is not None:
        template_path_value = getattr(meta, "template_path", None)
        if template_path_value is None and isinstance(meta, BaseModel):
            extra = getattr(meta, "model_extra", None)
            if isinstance(extra, dict):
                template_path_value = extra.get("template_path")
        if template_path_value is None and isinstance(meta, dict):
            template_path_value = meta.get("template_path")
        if template_path_value is not None and source_name is None:
            source_name = "template_config"

    if not template_path_value:
        try:
            raw_spec = json.loads(spec_source.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            raw_spec = {}
        if isinstance(raw_spec, dict):
            template_path_value = raw_spec.get("meta", {}).get("template_path")  # type: ignore[assignment]
            if template_path_value is not None and source_name is None:
                source_name = "template_config"

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


class _LLMLogFormatter(logging.Formatter):
    """slide_ai ログ用のサニタイズ済みフォーマッタ。"""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        for attr in (
            "slide_id",
            "card_id",
            "model",
            "intent",
            "reason",
            "finish_reason",
            "refusal",
            "warnings",
            "prompt_len",
            "response_len",
            "truncated",
        ):
            if not hasattr(record, attr):
                setattr(record, attr, "-")
        return super().format(record)


def configure_llm_logger(log_dir: Path | None = None) -> None:
    """slide_ai LLm ログのファイル・ストリーム出力を準備する。"""

    target_dir = log_dir or Path("logs")
    target_dir.mkdir(parents=True, exist_ok=True)
    llm_logger = logging.getLogger("pptx_generator.slide_ai.llm")
    formatter = _LLMLogFormatter(
        fmt=(
            "%(asctime)s %(levelname)s %(name)s "
            "slide_id=%(slide_id)s card_id=%(card_id)s model=%(model)s intent=%(intent)s "
            "reason=%(reason)s finish=%(finish_reason)s refusal=%(refusal)s warnings=%(warnings)s "
            "prompt_len=%(prompt_len)s response_len=%(response_len)s truncated=%(truncated)s message=%(message)s"
        ),
    )

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
            and getattr(handler, "baseFilename", None) == str(target_dir / "out.log")
        ),
        None,
    )
    if existing_handler:
        existing_handler.setFormatter(formatter)
    else:
        handler = RotatingFileHandler(
            target_dir / "out.log",
            encoding="utf-8",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
        )
        handler.setFormatter(formatter)
        llm_logger.addHandler(handler)

    stream_handler_exists = any(
        isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
        for handler in llm_logger.handlers
    )
    if not stream_handler_exists:
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        stream_handler.setFormatter(formatter)
        llm_logger.addHandler(stream_handler)
    llm_logger.setLevel(logging.INFO)
    llm_logger.propagate = False


def configure_file_logging(log_dir: Path | None = None) -> None:
    """`logs/out.log` へルートロガーの出力を複製するファイルハンドラを設定する。"""

    target_dir = log_dir or Path("logs")
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / "out.log"
    root_logger = logging.getLogger()
    if not any(
        isinstance(handler, logging.FileHandler)
        and getattr(handler, "baseFilename", None) == str(file_path)
        for handler in root_logger.handlers
    ):
        handler = RotatingFileHandler(
            file_path,
            encoding="utf-8",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
        )
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)


def dump_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")
    logger.info("Saved JSON to %s", path.resolve())
