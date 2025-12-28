import json

import pytest
from werkzeug.exceptions import HTTPException

from pptx_generator.api.flask_app import create_app
from pptx_generator.api.routes import _ensure_stage_artifacts, _registry_path
from pptx_generator.runtime.job_queue import InProcessJobQueue, JobRequest, JobState, JobStatus
from datetime import datetime, timezone


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

    assert resolved["jobspec_url"].endswith("template/new.json")
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

    assert resolved["jobspec_url"].endswith("template/pending.json")
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
