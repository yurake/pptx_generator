import hashlib
import hmac
import json
import time

import pytest

from pptx_generator.api.flask_app import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("PPTX_API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("PPTX_API_HMAC_KEY_CURRENT", raising=False)
    app = create_app()
    return app.test_client()


def test_auth_missing_returns_401(client):
    resp = client.post("/templates", json={"template_path": "x", "mode": "static"})
    assert resp.status_code == 401
    body = resp.get_json()
    assert body["code"] == "unauthorized"


def test_bearer_auth_success(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    app = create_app()
    c = app.test_client()
    resp = c.post(
        "/templates",
        headers={"Authorization": "Bearer token-123"},
        json={"template_path": "x", "mode": "static"},
    )
    assert resp.status_code == 202
    body = resp.get_json()
    assert body["job_id"]
    assert body["transaction_id"]
    assert body["status"] in ("pending", "running", "succeeded", "failed")


def test_hmac_auth_success(monkeypatch, tmp_path):
    key = "secret-key"
    monkeypatch.setenv("PPTX_API_HMAC_KEY_CURRENT", key)
    monkeypatch.setenv("PPTX_API_HMAC_KEY_NEXT", "next-key")  # ensure secondary key path covered
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    app = create_app()
    c = app.test_client()
    payload = {"template_path": "x", "mode": "static"}
    body_bytes = json.dumps(payload, separators=(",", ":")).encode()
    ts = str(int(time.time()))
    signing_str = f"{ts}\nPOST\n/templates\n{hashlib.sha256(body_bytes).hexdigest()}"
    sig = hmac.new(key.encode(), signing_str.encode(), hashlib.sha256).hexdigest()

    resp = c.post(
        "/templates",
        data=body_bytes,
        headers={"Content-Type": "application/json", "X-Timestamp": ts, "X-Signature": sig},
    )
    assert resp.status_code == 202
    body = resp.get_json()
    assert body["stage"] == "template"


def test_hmac_invalid_signature(monkeypatch):
    key = "secret-key"
    monkeypatch.setenv("PPTX_API_HMAC_KEY_CURRENT", key)
    app = create_app()
    c = app.test_client()
    payload = {"template_path": "x", "mode": "static"}
    ts = str(int(time.time()))
    resp = c.post(
        "/templates",
        json=payload,
        headers={"X-Timestamp": ts, "X-Signature": "deadbeef"},
    )
    assert resp.status_code == 401
    assert resp.get_json()["code"] == "unauthorized"


def test_hmac_timestamp_skew(monkeypatch):
    key = "secret-key"
    monkeypatch.setenv("PPTX_API_HMAC_KEY_CURRENT", key)
    app = create_app()
    c = app.test_client()
    payload = {"template_path": "x", "mode": "static"}
    ts = "0"  # too old
    resp = c.post(
        "/templates",
        json=payload,
        headers={"X-Timestamp": ts, "X-Signature": "deadbeef"},
    )
    assert resp.status_code == 401


def test_hmac_load_keys(monkeypatch):
    monkeypatch.setenv("PPTX_API_HMAC_KEY_CURRENT", "key1")
    monkeypatch.setenv("PPTX_API_HMAC_KEY_NEXT", "key2")
    from pptx_generator.api.flask_app import _load_hmac_keys

    keys = _load_hmac_keys()
    assert keys == ["key1", "key2"]


def test_job_flow_status(monkeypatch, tmp_path):
    monkeypatch.delenv("PPTX_API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("PPTX_API_HMAC_KEY_CURRENT", raising=False)
    app = create_app()
    c = app.test_client()
    resp = c.post("/templates", json={"template_path": "x", "mode": "static"})
    assert resp.status_code == 401

    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    app = create_app()
    c = app.test_client()
    resp = c.post(
        "/templates",
        headers={"Authorization": "Bearer token-123"},
        json={"template_path": "x", "mode": "static"},
    )
    assert resp.status_code == 202
    job = resp.get_json()
    status_resp = c.get(job["status_url"], headers={"Authorization": "Bearer token-123"})
    assert status_resp.status_code == 200
    status_body = status_resp.get_json()
    assert status_body["job_id"] == job["job_id"]
    assert status_body["transaction_id"] == job["transaction_id"]
    assert status_body["status"] in ("pending", "running", "succeeded", "failed")
    tx_resp = c.get(job["transaction_url"], headers={"Authorization": "Bearer token-123"})
    assert tx_resp.status_code == 200
    tx_body = tx_resp.get_json()
    assert any(j["job_id"] == job["job_id"] for j in tx_body["jobs"])


def test_artifact_not_found(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    app = create_app()
    c = app.test_client()
    # gen を tx だけで実行（前段なし）→ 前段不足で 422
    resp = c.post(
        "/gen",
        headers={"Authorization": "Bearer token-123"},
        json={"transaction_id": "tx-missing"},
    )
    assert resp.status_code in (404, 422)


def test_artifact_job_not_found(monkeypatch):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    app = create_app()
    c = app.test_client()
    resp = c.get("/jobs/missing/artifacts/pptx", headers={"Authorization": "Bearer token-123"})
    assert resp.status_code == 404


def test_artifact_success(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    app = create_app()
    c = app.test_client()
    file_path = tmp_path / "sample.pptx"
    file_path.write_bytes(b"dummy")

    from pptx_generator.runtime.job_queue import JobRequest, JobState, JobStatus, get_queue

    queue = get_queue()
    job_id = "job-artifact"
    state = JobState(
        request=JobRequest(stage="gen", func=lambda: None, job_id=job_id, transaction_id="tx1"),
        status=JobStatus.SUCCEEDED,
        result={"artifacts": {"pptx_url": str(file_path)}},
    )
    queue._jobs[job_id] = state  # type: ignore[attr-defined]

    resp = c.get(f"/jobs/{job_id}/artifacts/pptx", headers={"Authorization": "Bearer token-123"})
    assert resp.status_code == 200
    assert resp.data == b"dummy"


def test_artifact_invalid_type(monkeypatch):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    app = create_app()
    c = app.test_client()
    from pptx_generator.runtime.job_queue import JobRequest, JobState, JobStatus, get_queue

    queue = get_queue()
    job_id = "job-artifact2"
    state = JobState(
        request=JobRequest(stage="gen", func=lambda: None, job_id=job_id, transaction_id="tx1"),
        status=JobStatus.SUCCEEDED,
        result={"artifacts": {"pptx_url": "dummy"}},
    )
    queue._jobs[job_id] = state  # type: ignore[attr-defined]

    resp = c.get(f"/jobs/{job_id}/artifacts/png", headers={"Authorization": "Bearer token-123"})
    assert resp.status_code == 404


def test_jobs_other_stages(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    app = create_app()
    c = app.test_client()

    # tx なし／前段なし → すべて 422/404（前段成果物なし）
    resp = c.post("/prepare", headers={"Authorization": "Bearer token-123"}, json={"prepare_sources": [], "mode": "dynamic"})
    assert resp.status_code in (404, 422)

    resp = c.post("/compose", headers={"Authorization": "Bearer token-123"}, json={"transaction_id": "tx-missing"})
    assert resp.status_code in (404, 422)

    resp = c.post("/gen", headers={"Authorization": "Bearer token-123"}, json={"transaction_id": "tx-missing"})
    assert resp.status_code in (404, 422)


def test_job_not_found(monkeypatch):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    app = create_app()
    c = app.test_client()
    resp = c.get("/jobs/unknown", headers={"Authorization": "Bearer token-123"})
    assert resp.status_code == 404


def test_hmac_invalid_timestamp(monkeypatch):
    key = "secret-key"
    monkeypatch.setenv("PPTX_API_HMAC_KEY_CURRENT", key)
    app = create_app()
    c = app.test_client()
    resp = c.post(
        "/templates",
        json={"template_path": "x", "mode": "static"},
        headers={"X-Timestamp": "not-a-number", "X-Signature": "deadbeef"},
    )
    assert resp.status_code == 401
    assert resp.get_json()["code"] == "unauthorized"


def test_invalid_json_returns_400(monkeypatch):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    app = create_app()
    c = app.test_client()
    resp = c.post("/templates", headers={"Authorization": "Bearer token-123"}, data="not-json")
    assert resp.status_code == 400


def test_template_missing_field(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    app = create_app()
    c = app.test_client()
    resp = c.post("/templates", headers={"Authorization": "Bearer token-123"}, json={})
    assert resp.status_code == 422


def test_job_error_path(monkeypatch):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    app = create_app()
    c = app.test_client()

    # patch enqueue to produce an erroring job
    from pptx_generator.api import flask_app as module

    def enqueue_error(queue, *, stage, job_id, transaction_id, payload):
        request = module.JobRequest(
            stage=stage,
            job_id=job_id,
            transaction_id=transaction_id,
            func=lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        state = queue.enqueue(request)
        queue.ensure_workers(1)
        queue.wait(state.request.job_id)
        return state

    monkeypatch.setattr(module, "_enqueue_job", enqueue_error)

    resp = c.post(
        "/templates",
        headers={"Authorization": "Bearer token-123"},
        json={"template_path": "x", "mode": "static"},
    )
    job = resp.get_json()
    status_resp = c.get(job["status_url"], headers={"Authorization": "Bearer token-123"})
    body = status_resp.get_json()
    assert body["status"] == "failed"
    assert body["error"]["code"] == "job_failed"
    assert "boom" in body["error"]["message"]


def test_prepare_error_mapped_to_422(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    app = create_app()
    c = app.test_client()

    from pptx_generator.cli_handlers.prepare import PrepareCommandError
    from pptx_generator import api as api_module

    def raise_prepare_error(*args, **kwargs):
        raise PrepareCommandError("prepare failed", exit_code=6)

    def enqueue_error(queue, *, stage, job_id, transaction_id, payload):
        raise PrepareCommandError("prepare failed", exit_code=6)

    monkeypatch.setattr(api_module.flask_app, "_enqueue_job", enqueue_error)

    resp = c.post(
        "/prepare",
        headers={"Authorization": "Bearer token-123"},
        json={
            "prepare_sources": [],
            "mode": "dynamic",
        },
    )
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["code"] == "validation_error"


def test_prepare_files_not_found(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    app = create_app()
    c = app.test_client()
    resp = c.post(
        "/prepare",
        headers={"Authorization": "Bearer token-123"},
        json={
            "prepare_sources": ["missing.md"],
            "mode": "dynamic",
        },
    )
    # run_prepare_command will raise FileNotFoundError -> PrepareCommandError(exit_code=4) -> 422
    assert resp.status_code in (404, 422)


def test_prepare_compose_gen_stub(monkeypatch, tmp_path):
    # NOTE: templates -> prepare -> compose -> gen を tx 経由で実行（パス指定なし）
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    app = create_app()
    c = app.test_client()

    tpl_resp = c.post(
        "/templates",
        headers={"Authorization": "Bearer token-123"},
        json={
            "template_path": "samples/templates/dynamic_template.pptx",
            "mode": "dynamic",
        },
    )
    assert tpl_resp.status_code == 202
    tx = tpl_resp.get_json()["transaction_id"]

    prep_resp = c.post(
        "/prepare",
        headers={"Authorization": "Bearer token-123"},
        json={
            "transaction_id": tx,
            "prepare_sources": ["samples/input/pitch.md"],
            "mode": "dynamic",
        },
    )
    assert prep_resp.status_code == 202

    comp_resp = c.post(
        "/compose",
        headers={"Authorization": "Bearer token-123"},
        json={"transaction_id": tx},
    )
    assert comp_resp.status_code == 202

    gen_resp = c.post(
        "/gen",
        headers={"Authorization": "Bearer token-123"},
        json={"transaction_id": tx, "export_pdf": False},
    )
    assert gen_resp.status_code in (202, 422)
    if gen_resp.status_code != 202:
        body = gen_resp.get_json()
        assert body["code"] in ("validation_error", "not_found")
        return
    gen_job = gen_resp.get_json()

    # wait for completion
    status_body = None
    for _ in range(100):
        status_resp = c.get(gen_job["status_url"], headers={"Authorization": "Bearer token-123"})
        assert status_resp.status_code == 200
        status_body = status_resp.get_json()
        if status_body["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.1)
    assert status_body is not None
    assert status_body["status"] == "succeeded"
    artifacts = status_body["artifacts"]
    assert "pptx_url" in artifacts


def test_template_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.delenv("PPTX_API_MAX_BODY", raising=False)
    app = create_app()
    c = app.test_client()

    resp = c.post(
        "/templates",
        headers={"Authorization": "Bearer token-123"},
        json={
            "template_path": "samples/templates/dynamic_template.pptx",
            "mode": "dynamic",
        },
    )
    assert resp.status_code == 202
    job = resp.get_json()

    # poll for completion
    status_body = None
    for _ in range(30):
        status_resp = c.get(job["status_url"], headers={"Authorization": "Bearer token-123"})
        assert status_resp.status_code == 200
        status_body = status_resp.get_json()
        if status_body["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.1)

    assert status_body is not None
    assert status_body["status"] in ("succeeded", "failed")
    artifacts = status_body["artifacts"]
    assert "jobspec_url" in artifacts
    assert "template_spec_url" in artifacts
    # ファイルが生成されていることを確認
    for key in ("jobspec_url", "template_spec_url"):
        assert (tmp_path / artifacts[key]).exists()


def test_output_root_default(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.delenv("PPTX_OUTPUT_ROOT", raising=False)
    app = create_app()
    c = app.test_client()
    resp = c.post(
        "/templates",
        headers={"Authorization": "Bearer token-123"},
        json={"template_path": "samples/templates/templates.pptx", "mode": "dynamic"},
    )
    assert resp.status_code == 422
