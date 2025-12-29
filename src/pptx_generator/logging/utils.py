from __future__ import annotations

import logging
import sys
from logging import Handler
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pptx_generator.logging import LoggingContextFilter, attach_context_filter

LOG_FORMAT = (
    "%(asctime)s %(levelname)s %(name)s job=%(job_id)s tx=%(transaction_id)s "
    "stage=%(stage)s req=%(request_id)s %(message)s"
)
DEFAULT_LOG_FILENAME = "out.log"
_DEFAULT_MAX_BYTES = 10 * 1024 * 1024
_DEFAULT_BACKUP_COUNT = 5


def _resolve_log_dir(log_dir: Path | str | None) -> Path:
    path = Path(log_dir) if log_dir is not None else Path("logs")
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_stream_handler(
    logger: logging.Logger,
    *,
    level: int,
    formatter: logging.Formatter | None = None,
    stream: object = sys.stdout,
) -> Handler:
    """ロガーに指定ストリームのハンドラがなければ追加し、レベルとフォーマットを整える。"""

    formatter = formatter or logging.Formatter(LOG_FORMAT)
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and getattr(handler, "stream", None) is stream:
            handler.setLevel(level)
            handler.setFormatter(formatter)
            attach_context_filter(logger)
            if not any(isinstance(f, LoggingContextFilter) for f in handler.filters):
                handler.addFilter(LoggingContextFilter())
            return handler

    handler = logging.StreamHandler(stream=stream)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    handler.addFilter(LoggingContextFilter())
    attach_context_filter(logger)
    return handler


def ensure_rotating_file_handler(
    logger: logging.Logger,
    *,
    file_path: Path,
    level: int,
    formatter: logging.Formatter | None = None,
) -> Handler:
    """ロガーに対象ファイル向けのローテーションハンドラを追加（既存なら更新）する。"""

    formatter = formatter or logging.Formatter(LOG_FORMAT)
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and getattr(handler, "baseFilename", None) == str(file_path):
            handler.setLevel(level)
            handler.setFormatter(formatter)
            attach_context_filter(logger)
            if not any(isinstance(f, LoggingContextFilter) for f in handler.filters):
                handler.addFilter(LoggingContextFilter())
            return handler

    handler = RotatingFileHandler(
        file_path,
        encoding="utf-8",
        maxBytes=_DEFAULT_MAX_BYTES,
        backupCount=_DEFAULT_BACKUP_COUNT,
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    handler.addFilter(LoggingContextFilter())
    attach_context_filter(logger)
    return handler


def clear_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)


def configure_root_logging(
    *,
    level: int,
    log_dir: Path | str | None = None,
    add_stderr: bool = False,
    stderr_level: int = logging.ERROR,
) -> logging.Logger:
    """標準出力とログファイルを併用するルートロガー設定を行う。"""

    formatter = logging.Formatter(LOG_FORMAT)
    target_dir = _resolve_log_dir(log_dir)
    handlers = [
        logging.StreamHandler(stream=sys.stdout),
    ]
    handlers[0].setLevel(level)
    handlers[0].setFormatter(formatter)

    if add_stderr:
        stderr_handler = logging.StreamHandler(stream=sys.stderr)
        stderr_handler.setLevel(stderr_level)
        stderr_handler.setFormatter(formatter)
        handlers.append(stderr_handler)

    file_handler = RotatingFileHandler(
        target_dir / DEFAULT_LOG_FILENAME,
        encoding="utf-8",
        maxBytes=_DEFAULT_MAX_BYTES,
        backupCount=_DEFAULT_BACKUP_COUNT,
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        handlers=handlers,
        force=True,
    )
    root = logging.getLogger()
    for handler in root.handlers:
        if not any(isinstance(f, LoggingContextFilter) for f in handler.filters):
            handler.addFilter(LoggingContextFilter())
    attach_context_filter(root)
    return root
