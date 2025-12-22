from __future__ import annotations

import contextvars
from dataclasses import dataclass


@dataclass(slots=True)
class JobContext:
    job_id: str
    transaction_id: str


_current_job: contextvars.ContextVar[JobContext | None] = contextvars.ContextVar(
    "pptx_generator_current_job",
    default=None,
)


def set_current_job(job_id: str, transaction_id: str) -> contextvars.Token[JobContext | None]:
    return _current_job.set(JobContext(job_id=job_id, transaction_id=transaction_id))


def reset_current_job(token: contextvars.Token[JobContext | None]) -> None:
    _current_job.reset(token)


def get_current_job() -> JobContext | None:
    return _current_job.get()


__all__ = ["JobContext", "set_current_job", "reset_current_job", "get_current_job"]
