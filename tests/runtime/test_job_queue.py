from __future__ import annotations

import pytest

from pptx_generator.models import JobAuth, JobMeta, JobSpec
from pptx_generator.pipeline import PipelineContext
from pptx_generator.runtime.job_context import get_current_job
from pptx_generator.runtime.job_queue import JobStatus, get_queue, run_job_sync


def setup_function() -> None:
    get_queue().reset()


def _build_stub_spec() -> JobSpec:
    return JobSpec(
        meta=JobMeta(schema_version="1.0", title="test"),
        auth=JobAuth(created_by="tester"),
        slides=[],
    )


def test_run_job_sync_applies_job_ids(tmp_path) -> None:
    job_id = "job-sync-1"
    tx_id = "tx-sync-1"

    def task() -> tuple[str, str, str | None]:
        context = PipelineContext(spec=_build_stub_spec(), workdir=tmp_path)
        current = get_current_job()
        return context.job_id, context.transaction_id, current.job_id if current else None

    result = run_job_sync(stage="prepare", func=task, job_id=job_id, transaction_id=tx_id)
    ctx_job_id, ctx_tx_id, current_job_id = result
    assert ctx_job_id == job_id
    assert ctx_tx_id == tx_id
    assert current_job_id == job_id


def test_run_job_sync_raises_exceptions(tmp_path) -> None:
    def task() -> None:
        _ = PipelineContext(spec=_build_stub_spec(), workdir=tmp_path)
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        run_job_sync(stage="gen", func=task)

    # ジョブ記録が残っていることを簡易確認
    queue = get_queue()
    job_states = [state for state in queue._jobs.values()]  # type: ignore[attr-defined]
    assert any(state.status == JobStatus.FAILED for state in job_states)


def test_run_job_sync_reraises_base_exception(tmp_path) -> None:
    def task() -> None:
        _ = PipelineContext(spec=_build_stub_spec(), workdir=tmp_path)
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        run_job_sync(stage="gen", func=task)

    queue = get_queue()
    job_states = [state for state in queue._jobs.values()]  # type: ignore[attr-defined]
    assert any(state.status == JobStatus.FAILED for state in job_states)


def test_run_job_sync_sets_done_event_even_on_error(tmp_path) -> None:
    def task() -> None:
        _ = PipelineContext(spec=_build_stub_spec(), workdir=tmp_path)
        raise RuntimeError("fail-done")

    with pytest.raises(RuntimeError, match="fail-done"):
        run_job_sync(stage="prepare", func=task)

    queue = get_queue()
    job_states = [state for state in queue._jobs.values()]  # type: ignore[attr-defined]
    assert any(state.done.is_set() for state in job_states)
    assert any(state.status == JobStatus.FAILED for state in job_states)


def test_run_job_sync_handles_multiple_jobs(tmp_path) -> None:
    def task(payload: str) -> str:
        _ = PipelineContext(spec=_build_stub_spec(), workdir=tmp_path)
        return payload

    queue = get_queue()
    res1 = run_job_sync(stage="gen", func=lambda: task("a"))
    res2 = run_job_sync(stage="prepare", func=lambda: task("b"))

    assert res1 == "a"
    assert res2 == "b"
    job_states = [state for state in queue._jobs.values()]  # type: ignore[attr-defined]
    assert all(state.status == JobStatus.SUCCEEDED for state in job_states)
    assert all(state.done.is_set() for state in job_states)
