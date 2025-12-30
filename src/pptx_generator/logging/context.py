from __future__ import annotations

import contextvars
import logging
from typing import Any

from pptx_generator.runtime.job_context import get_current_job

_current_stage: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "pptx_generator_current_stage",
    default=None,
)

_current_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "pptx_generator_current_request_id",
    default=None,
)


def set_current_stage(stage: str | None) -> contextvars.Token[str | None]:
    return _current_stage.set(stage)


def reset_current_stage(token: contextvars.Token[str | None]) -> None:
    _current_stage.reset(token)


def set_current_request_id(request_id: str | None) -> contextvars.Token[str | None]:
    return _current_request_id.set(request_id)


def reset_current_request_id(token: contextvars.Token[str | None]) -> None:
    _current_request_id.reset(token)


class LoggingContextFilter(logging.Filter):
    """job/tx/stage/request_id をログレコードへ注入するフィルタ。"""

    def __init__(self, name: str = "") -> None:
        super().__init__(name)

    @staticmethod
    def _shorten(value: str | None) -> str:
        return (value or "-")[:8]

    def filter(self, record: logging.LogRecord) -> bool:
        job = get_current_job()
        record.job_id = self._shorten(getattr(job, "job_id", None))
        record.transaction_id = self._shorten(getattr(job, "transaction_id", None))
        record.stage = (record.stage if hasattr(record, "stage") else None) or _current_stage.get() or "-"
        record.request_id = self._shorten(_current_request_id.get())
        return True


def attach_context_filter(logger: logging.Logger) -> None:
    if any(isinstance(f, LoggingContextFilter) for f in logger.filters):
        return
    logger.addFilter(LoggingContextFilter())


__all__ = [
    "LoggingContextFilter",
    "attach_context_filter",
    "set_current_stage",
    "reset_current_stage",
    "set_current_request_id",
    "reset_current_request_id",
]
