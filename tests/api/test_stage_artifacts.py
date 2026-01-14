import json
import multiprocessing
import threading
from pathlib import Path

import pytest
from werkzeug.exceptions import HTTPException

from pptx_generator.api.flask_app import create_app
from pptx_generator.api.routes import (
    _ensure_stage_artifacts,
    _registry_backup_path,
    _registry_lock_path,
    _registry_path,
    _update_registry,
)
from pptx_generator.runtime.job_queue import InProcessJobQueue, JobRequest, JobState, JobStatus
from datetime import datetime, timezone
from pathlib import Path


def _proc_update_registry(tx_root_str: str, stage: str, artifact_rel: str, barrier):
    from pptx_generator.api.routes import _update_registry
    from pptx_generator.runtime.job_queue import JobRequest, JobState, JobStatus

    tx_root = Path(tx_root_str)
    artifact_path = tx_root / artifact_rel
    request = JobRequest(stage=stage, func=lambda: None, transaction_id="tx-proc", job_id=f"job-{stage}")
    state = JobState(
        request=request,
        status=JobStatus.SUCCEEDED,
        result={"artifacts": {"pptx_url": str(artifact_path)}},
    )
    barrier.wait()
    _update_registry(tx_root, stage, state)


@pytest.fixture
def api_app(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.delenv("PPTX_API_HMAC_KEY_CURRENT", raising=False)
    return create_app()


def test_ensure_stage_artifacts_returns_404_when_transaction_missing(api_app, tmp_path):
    queue = InProcessJobQueue()
    with api_app.app_context(), pytest.raises(HTTPException) as excinfo:
        _ensure_stage_artifacts(queue, tmp_path, "tx-1", "template", ["jobspec_url"])
    assert excinfo.value.response.status_code == 404


def test_ensure_stage_artifacts_allows_missing_flag(api_app, tmp_path):
    queue = InProcessJobQueue()
    with api_app.app_context():
        resolved = _ensure_stage_artifacts(
            queue, tmp_path, "tx-2", "template", ["jobspec_url"], allow_missing=True
        )
    assert resolved == {}


def test_allow_missing_returns_empty_when_entry_has_no_artifacts(api_app, tmp_path):
    registry_path = _registry_path(tmp_path)
    registry_path.write_text(json.dumps({"template": {"job_id": "123"}}, ensure_ascii=False), encoding="utf-8")
    queue = InProcessJobQueue()
    with api_app.app_context():
        resolved = _ensure_stage_artifacts(
            queue, tmp_path, "tx-2a", "template", ["jobspec_url"], allow_missing=True
        )
    assert resolved == {}


def test_ensure_stage_artifacts_returns_422_when_stage_not_in_registry(api_app, tmp_path):
    registry_path = _registry_path(tmp_path)
    registry_path.write_text(json.dumps({"other": {"artifacts": {}}}), encoding="utf-8")
    queue = InProcessJobQueue()
    with api_app.app_context(), pytest.raises(HTTPException) as excinfo:
        _ensure_stage_artifacts(queue, tmp_path, "tx-3", "template", ["jobspec_url"])
    assert excinfo.value.response.status_code == 422


def test_ensure_stage_artifacts_requires_artifacts_field(api_app, tmp_path):
    registry_path = _registry_path(tmp_path)
    registry_path.write_text(json.dumps({"template": {"job_id": "123"}}, ensure_ascii=False), encoding="utf-8")
    queue = InProcessJobQueue()
    with api_app.app_context(), pytest.raises(HTTPException) as excinfo:
        _ensure_stage_artifacts(queue, tmp_path, "tx-4", "template", ["jobspec_url"])
    assert excinfo.value.response.status_code == 422


def test_missing_requested_artifact_key_returns_422(api_app, tmp_path):
    registry_path = _registry_path(tmp_path)
    registry_path.write_text(
        json.dumps({"template": {"artifacts": {"jobspec_url": "template/job.json"}}}, ensure_ascii=False),
        encoding="utf-8",
    )
    queue = InProcessJobQueue()
    with api_app.app_context(), pytest.raises(HTTPException) as excinfo:
        _ensure_stage_artifacts(queue, tmp_path, "tx-4a", "template", ["prepare_card_url"])
    assert excinfo.value.response.status_code == 422


def test_entry_not_dict_returns_empty_when_allow_missing(api_app, tmp_path):
    registry_path = _registry_path(tmp_path)
    registry_path.write_text(json.dumps({"template": []}, ensure_ascii=False), encoding="utf-8")
    queue = InProcessJobQueue()
    with api_app.app_context():
        resolved = _ensure_stage_artifacts(queue, tmp_path, "tx-4b", "template", ["jobspec_url"], allow_missing=True)
    assert resolved == {}


def test_entry_not_dict_returns_422_when_not_allow_missing(api_app, tmp_path):
    registry_path = _registry_path(tmp_path)
    registry_path.write_text(json.dumps({"template": []}, ensure_ascii=False), encoding="utf-8")
    queue = InProcessJobQueue()
    with api_app.app_context(), pytest.raises(HTTPException) as excinfo:
        _ensure_stage_artifacts(queue, tmp_path, "tx-4c", "template", ["jobspec_url"])
    assert excinfo.value.response.status_code == 422


def test_ensure_stage_artifacts_loads_latest_job_success(api_app, tmp_path):
    queue = InProcessJobQueue()
    artifacts = {"jobspec_url": "artifacts/jobspec.json"}
    request = JobRequest(stage="template", func=lambda: None, transaction_id="tx-5")
    state = JobState(
        request=request,
        status=JobStatus.SUCCEEDED,
        result={"artifacts": artifacts},
        finished_at=datetime.now(timezone.utc),
    )
    queue._jobs[request.job_id] = state  # type: ignore[attr-defined]

    with api_app.app_context():
        resolved = _ensure_stage_artifacts(queue, tmp_path, "tx-5", "template", ["jobspec_url"])

    assert resolved["jobspec_url"] == str((tmp_path / artifacts["jobspec_url"]).resolve())


def test_registry_updates_with_newer_job(api_app, tmp_path):
    queue = InProcessJobQueue()
    tx_id = "tx-6"
    old_request = JobRequest(stage="template", func=lambda: None, transaction_id=tx_id, job_id="old-job")
    new_request = JobRequest(stage="template", func=lambda: None, transaction_id=tx_id, job_id="new-job")

    old_state = JobState(
        request=old_request,
        status=JobStatus.SUCCEEDED,
        result={"artifacts": {"jobspec_url": str(tmp_path / "template" / "old.json")}},
        finished_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    new_state = JobState(
        request=new_request,
        status=JobStatus.SUCCEEDED,
        result={"artifacts": {"jobspec_url": str(tmp_path / "template" / "new.json")}},
        finished_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )
    queue._jobs[old_request.job_id] = old_state  # type: ignore[attr-defined]
    queue._jobs[new_request.job_id] = new_state  # type: ignore[attr-defined]

    # 旧ジョブで一度 registry を作成
    _ensure_stage_artifacts(queue, tmp_path, tx_id, "template", ["jobspec_url"])

    # 新しいジョブが最新として後勝ちで反映されることを確認
    with api_app.app_context():
        resolved = _ensure_stage_artifacts(queue, tmp_path, tx_id, "template", ["jobspec_url"])

    assert Path(resolved["jobspec_url"]).as_posix().endswith("template/new.json")
    registry = json.loads(_registry_path(tmp_path).read_text(encoding="utf-8"))
    assert registry["template"]["job_id"] == "new-job"


def test_pending_job_waits_and_updates_registry(api_app, tmp_path):
    request = JobRequest(stage="template", func=lambda: None, transaction_id="tx-7", job_id="pending-job")
    state = JobState(
        request=request,
        status=JobStatus.PENDING,
        result=None,
        finished_at=None,
    )

    class DummyQueue(InProcessJobQueue):  # type: ignore[misc]
        def __init__(self, initial_state):
            super().__init__()
            self._jobs[initial_state.request.job_id] = initial_state  # type: ignore[attr-defined]

        def wait(self, job_id: str, timeout: float | None = None):
            job_state = self._jobs[job_id]  # type: ignore[attr-defined]
            job_state.status = JobStatus.SUCCEEDED
            job_state.result = {"artifacts": {"jobspec_url": "template/pending.json"}}
            job_state.finished_at = datetime.now(timezone.utc)
            job_state.done.set()
            return job_state

        def get_job(self, job_id: str):
            return self._jobs.get(job_id)  # type: ignore[attr-defined]

    queue = DummyQueue(state)

    with api_app.app_context():
        resolved = _ensure_stage_artifacts(queue, tmp_path, "tx-7", "template", ["jobspec_url"])

    assert Path(resolved["jobspec_url"]).as_posix().endswith("template/pending.json")
    registry = json.loads(_registry_path(tmp_path).read_text(encoding="utf-8"))
    assert registry["template"]["job_id"] == "pending-job"


def test_failed_latest_job_without_entry_returns_422(api_app, tmp_path):
    request = JobRequest(stage="template", func=lambda: None, transaction_id="tx-8", job_id="failed-job")
    state = JobState(
        request=request,
        status=JobStatus.FAILED,
        result=None,
        finished_at=datetime.now(timezone.utc),
    )
    queue = InProcessJobQueue()
    queue._jobs[request.job_id] = state  # type: ignore[attr-defined]

    with api_app.app_context(), pytest.raises(HTTPException) as excinfo:
        _ensure_stage_artifacts(queue, tmp_path, "tx-8", "template", ["jobspec_url"])

    assert excinfo.value.response.status_code == 422


def test_failed_latest_job_with_entry_without_artifacts_returns_422(api_app, tmp_path):
    request = JobRequest(stage="template", func=lambda: None, transaction_id="tx-9", job_id="failed-job")
    state = JobState(
        request=request,
        status=JobStatus.FAILED,
        result=None,
        finished_at=datetime.now(timezone.utc),
    )
    queue = InProcessJobQueue()
    queue._jobs[request.job_id] = state  # type: ignore[attr-defined]

    registry_path = _registry_path(tmp_path)
    registry_path.write_text(json.dumps({"template": {"job_id": "old-job"}}, ensure_ascii=False), encoding="utf-8")

    with api_app.app_context(), pytest.raises(HTTPException) as excinfo:
        _ensure_stage_artifacts(queue, tmp_path, "tx-9", "template", ["jobspec_url"])

    assert excinfo.value.response.status_code == 422


def test_missing_registry_returns_404(api_app, tmp_path):
    # registry file not created -> should return 404 when allow_missing is False
    queue = InProcessJobQueue()
    with api_app.app_context(), pytest.raises(HTTPException) as excinfo:
        _ensure_stage_artifacts(queue, tmp_path, "tx-10", "template", ["jobspec_url"])
    assert excinfo.value.response.status_code == 404


def test_update_registry_uses_lock_and_preserves_entries(tmp_path):
    barrier = threading.Barrier(2)

    def run(stage: str, artifact_path: Path):
        request = JobRequest(stage=stage, func=lambda: None, transaction_id="tx-lock", job_id=f"job-{stage}")
        state = JobState(
            request=request,
            status=JobStatus.SUCCEEDED,
            result={"artifacts": {"pptx_url": str(artifact_path)}},
        )
        barrier.wait()
        _update_registry(tmp_path, stage, state)

    template_artifact = tmp_path / "template" / "out1.pptx"
    prepare_artifact = tmp_path / "prepare" / "out2.pptx"
    for artifact in (template_artifact, prepare_artifact):
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("x")

    threads = [
        threading.Thread(target=run, args=("template", template_artifact)),
        threading.Thread(target=run, args=("prepare", prepare_artifact)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    registry = json.loads(_registry_path(tmp_path).read_text(encoding="utf-8"))
    assert registry["template"]["artifacts"]["pptx_url"] == str(template_artifact.relative_to(tmp_path))
    assert registry["prepare"]["artifacts"]["pptx_url"] == str(prepare_artifact.relative_to(tmp_path))
    assert _registry_lock_path(tmp_path).exists()


def test_update_registry_across_processes(tmp_path):
    import pptx_generator.api.routes as routes_module

    if getattr(routes_module, "fcntl", None) is None and getattr(routes_module, "msvcrt", None) is None:
        pytest.skip("file locking unavailable in this environment")

    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    template_artifact = tmp_path / "template" / "proc1.pptx"
    prepare_artifact = tmp_path / "prepare" / "proc2.pptx"
    for artifact in (template_artifact, prepare_artifact):
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("x")

    processes = [
        ctx.Process(
            target=_proc_update_registry,
            args=(str(tmp_path), "template", str(template_artifact.relative_to(tmp_path)), barrier),
        ),
        ctx.Process(
            target=_proc_update_registry,
            args=(str(tmp_path), "prepare", str(prepare_artifact.relative_to(tmp_path)), barrier),
        ),
    ]
    for proc in processes:
        proc.start()
    for proc in processes:
        proc.join(timeout=10)
        assert proc.exitcode == 0

    registry = json.loads(_registry_path(tmp_path).read_text(encoding="utf-8"))
    assert registry["template"]["artifacts"]["pptx_url"] == str(template_artifact.relative_to(tmp_path))
    assert registry["prepare"]["artifacts"]["pptx_url"] == str(prepare_artifact.relative_to(tmp_path))


def test_corrupted_registry_uses_backup_and_preserves_entries(tmp_path):
    queue = InProcessJobQueue()
    tx_id = "tx-backup"

    def make_state(stage: str, artifact_rel: str):
        request = JobRequest(stage=stage, func=lambda: None, transaction_id=tx_id, job_id=f"job-{stage}")
        return JobState(
            request=request,
            status=JobStatus.SUCCEEDED,
            result={"artifacts": {"pptx_url": artifact_rel}},
        )

    # 初回書き込みで registry を生成
    first_state = make_state("template", "template/base.pptx")
    _update_registry(tmp_path, "template", first_state)

    # 正常内容をバックアップに保存
    registry_path = _registry_path(tmp_path)
    backup_path = _registry_backup_path(tmp_path)
    backup_path.write_bytes(registry_path.read_bytes())

    # registry を破損させる
    registry_path.write_text("{invalid_json", encoding="utf-8")

    # backup を元に新しいステージを書き込みできることを確認
    second_state = make_state("prepare", "prepare/next.pptx")
    _update_registry(tmp_path, "prepare", second_state)

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    assert registry["template"]["artifacts"]["pptx_url"] == "template/base.pptx"
    assert registry["prepare"]["artifacts"]["pptx_url"] == "prepare/next.pptx"
