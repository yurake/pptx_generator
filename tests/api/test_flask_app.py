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


def test_bearer_auth_success(monkeypatch):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
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
    assert body["status"] == "pending"


def test_hmac_auth_success(monkeypatch):
    key = "secret-key"
    monkeypatch.setenv("PPTX_API_HMAC_KEY_CURRENT", key)
    monkeypatch.setenv("PPTX_API_HMAC_KEY_NEXT", "next-key")  # ensure secondary key path covered
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


def test_job_flow_status(monkeypatch):
    monkeypatch.delenv("PPTX_API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("PPTX_API_HMAC_KEY_CURRENT", raising=False)
    app = create_app()
    c = app.test_client()
    resp = c.post("/templates", json={"template_path": "x", "mode": "static"})
    assert resp.status_code == 401

    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
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


def test_artifact_not_found(monkeypatch):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    app = create_app()
    c = app.test_client()
    resp = c.post(
        "/gen",
        headers={"Authorization": "Bearer token-123"},
        json={"compose_job_id": "cmp1"},
    )
    job = resp.get_json()
    art_resp = c.get(
        f"/jobs/{job['job_id']}/artifacts/pptx", headers={"Authorization": "Bearer token-123"}
    )
    assert art_resp.status_code == 404
    assert art_resp.get_json()["code"] == "not_found"


def test_jobs_other_stages(monkeypatch):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    app = create_app()
    c = app.test_client()
    for path, stage in [("/prepare", "prepare"), ("/compose", "compose"), ("/gen", "gen")]:
        resp = c.post(path, headers={"Authorization": "Bearer token-123"}, json={})
        assert resp.status_code == 202
        body = resp.get_json()
        assert body["stage"] == stage


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
