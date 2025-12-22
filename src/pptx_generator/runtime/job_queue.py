from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from queue import Empty, Queue
from typing import Callable, Generic, TypeVar
from uuid import uuid4

from .job_context import JobContext, get_current_job, reset_current_job, set_current_job

T = TypeVar("T")


class JobStatus(str):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(slots=True)
class JobRequest(Generic[T]):
    stage: str
    func: Callable[[], T]
    job_id: str = field(default_factory=lambda: uuid4().hex)
    transaction_id: str = field(default_factory=lambda: uuid4().hex)
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class JobState(Generic[T]):
    request: JobRequest[T]
    status: str = JobStatus.PENDING
    result: T | None = None
    error: BaseException | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    done: threading.Event = field(default_factory=threading.Event)


class InProcessJobQueue:
    """メモリ管理のシンプルなジョブキュー。"""

    def __init__(self) -> None:
        self._queue: Queue[str] = Queue()
        self._jobs: dict[str, JobState[object]] = {}
        self._workers_started = 0
        self._lock = threading.Lock()

    def ensure_workers(self, count: int) -> None:
        with self._lock:
            while self._workers_started < count:
                thread = threading.Thread(target=self._worker_loop, daemon=True)
                thread.start()
                self._workers_started += 1

    def enqueue(self, request: JobRequest[T]) -> JobState[T]:
        state: JobState[T] = JobState(request=request)
        with self._lock:
            self._jobs[request.job_id] = state  # type: ignore[assignment]
        self._queue.put(request.job_id)
        return state

    def _worker_loop(self) -> None:
        while True:
            try:
                job_id = self._queue.get(timeout=1.0)
            except Empty:
                continue
            state = self._jobs.get(job_id)
            if state is None:
                self._queue.task_done()
                continue
            self._run_job(state)
            self._queue.task_done()

    def _run_job(self, state: JobState[object]) -> None:
        state.status = JobStatus.RUNNING
        state.started_at = datetime.now(timezone.utc)
        token = set_current_job(state.request.job_id, state.request.transaction_id)
        try:
            state.result = state.request.func()
            state.status = JobStatus.SUCCEEDED
        except BaseException as exc:  # noqa: BLE001
            state.error = exc
            state.status = JobStatus.FAILED
        finally:
            reset_current_job(token)
            state.finished_at = datetime.now(timezone.utc)
            state.done.set()

    def wait(self, job_id: str, timeout: float | None = None) -> JobState[object]:
        state = self._jobs[job_id]
        state.done.wait(timeout=timeout)
        return state

    def run_and_wait(self, request: JobRequest[T], worker_count: int = 1) -> JobState[T]:
        state = self.enqueue(request)
        self.ensure_workers(worker_count)
        completed = self.wait(request.job_id)
        return completed  # type: ignore[return-value]

    def reset(self) -> None:
        """テスト用にジョブ情報をリセットする。"""
        with self._lock:
            self._jobs.clear()
            while True:
                try:
                    self._queue.get_nowait()
                except Empty:
                    break
                else:
                    self._queue.task_done()

    def get_job(self, job_id: str) -> JobState[object] | None:
        return self._jobs.get(job_id)


_GLOBAL_QUEUE = InProcessJobQueue()


def get_queue() -> InProcessJobQueue:
    return _GLOBAL_QUEUE


def run_job_sync(
    *,
    stage: str,
    func: Callable[[], T],
    job_id: str | None = None,
    transaction_id: str | None = None,
    worker_count: int = 1,
) -> T:
    """ジョブをキューに投入し、完了まで待機する（同期）。"""
    job_request: JobRequest[T] = JobRequest(
        stage=stage,
        func=func,
        job_id=job_id or uuid4().hex,
        transaction_id=transaction_id or uuid4().hex,
    )
    queue = get_queue()
    state = queue.run_and_wait(job_request, worker_count=worker_count)
    if state.error:
        # 元例外を呼び出し元へ伝搬させる
        raise state.error
    return state.result  # type: ignore[return-value]


__all__ = [
    "JobStatus",
    "JobRequest",
    "JobState",
    "InProcessJobQueue",
    "get_queue",
    "run_job_sync",
]
