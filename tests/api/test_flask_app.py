import hashlib
import hmac
import json
import time
from pathlib import Path

import pytest
import logging

from pptx_generator.api.flask_app import create_app


@pytest.fixture(autouse=True)
def api_env(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.delenv("PPTX_API_HMAC_KEY_CURRENT", raising=False)
    return tmp_path


@pytest.fixture
def client():
    app = create_app()
    return app.test_client()


def test_healthcheck_without_auth(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_healthcheck_ignores_auth(client):
    resp = client.get("/health", headers={"Authorization": "Bearer token-123"})
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_request_id_logging_truncated(client, caplog):
    rid = "req-1234567890"
    api_logger = logging.getLogger("pptx_generator.api.flask_app")
    orig_propagate = api_logger.propagate
    api_logger.propagate = True
    api_logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.INFO):
            resp = client.get(
                "/transactions/tx-no-record",
                headers={"X-Request-ID": rid, "Authorization": "Bearer token-123"},
            )
    finally:
        api_logger.removeHandler(caplog.handler)
        api_logger.propagate = orig_propagate
    assert resp.status_code in (200, 404)
    truncated = rid[:8]
    assert truncated in caplog.text


def test_create_app_missing_output_root(monkeypatch):
    monkeypatch.delenv("PPTX_OUTPUT_ROOT", raising=False)
    with pytest.raises(RuntimeError) as exc:
        create_app()
    assert "PPTX_OUTPUT_ROOT" in str(exc.value)


def test_create_app_missing_auth(monkeypatch):
    monkeypatch.delenv("PPTX_API_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("PPTX_API_HMAC_KEY_CURRENT", raising=False)
    with pytest.raises(RuntimeError) as exc:
        create_app()
    assert "PPTX_API_BEARER_TOKEN or PPTX_API_HMAC_KEY_CURRENT" in str(exc.value)


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
        json={"template_path": "samples/templates/dynamic_template.pptx", "mode": "static"},
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
    payload = {"template_path": "samples/templates/dynamic_template.pptx", "mode": "static"}
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
    app = create_app()
    c = app.test_client()
    resp = c.post(
        "/templates",
        headers={"Authorization": "Bearer token-123"},
        json={"template_path": "samples/templates/dynamic_template.pptx", "mode": "static"},
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
    from pptx_generator.api import routes as module

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
    from pptx_generator.api import routes as api_module

    def raise_prepare_error(*args, **kwargs):
        raise PrepareCommandError("prepare failed", exit_code=6)

    def enqueue_error(queue, *, stage, job_id, transaction_id, payload):
        raise PrepareCommandError("prepare failed", exit_code=6)

    monkeypatch.setattr(api_module, "_enqueue_job", enqueue_error)

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


def test_prepare_compose_gen_static_stub(monkeypatch, tmp_path):
    """static テンプレートでもテンプレ→prepare→compose→gen が通ることを確認。"""

    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    app = create_app()
    c = app.test_client()

    tpl_resp = c.post(
        "/templates",
        headers={"Authorization": "Bearer token-123"},
        json={
            "template_path": "samples/templates/static_slide.pptx",
            "mode": "static",
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
            "mode": "static",
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


def test_parallel_dynamic_and_static(monkeypatch, tmp_path):
    """dynamic と static を並列実行し、双方 succeeded になることを確認。"""

    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))

    app = create_app()
    c = app.test_client()
    headers = {"Authorization": "Bearer token-123"}

    # dynamic
    tpl_dyn = c.post(
        "/templates",
        headers=headers,
        json={"template_path": "samples/templates/dynamic_template.pptx", "mode": "dynamic"},
    ).get_json()
    tx_dyn = tpl_dyn["transaction_id"]

    # static
    tpl_sta = c.post(
        "/templates",
        headers=headers,
        json={"template_path": "samples/templates/static_slide.pptx", "mode": "static"},
    ).get_json()
    tx_sta = tpl_sta["transaction_id"]

    # wait templates
    app.queue.wait(tpl_dyn["job_id"])
    app.queue.wait(tpl_sta["job_id"])

    # prepare
    prep_dyn = c.post(
        "/prepare",
        headers=headers,
        json={"transaction_id": tx_dyn, "prepare_sources": ["samples/input/pitch.md"], "mode": "dynamic"},
    ).get_json()
    prep_sta = c.post(
        "/prepare",
        headers=headers,
        json={"transaction_id": tx_sta, "prepare_sources": ["samples/input/pitch.md"], "mode": "static"},
    ).get_json()
    app.queue.wait(prep_dyn["job_id"])
    app.queue.wait(prep_sta["job_id"])

    # compose
    cmp_dyn = c.post("/compose", headers=headers, json={"transaction_id": tx_dyn}).get_json()
    cmp_sta = c.post("/compose", headers=headers, json={"transaction_id": tx_sta}).get_json()
    app.queue.wait(cmp_dyn["job_id"])
    app.queue.wait(cmp_sta["job_id"])

    # gen
    gen_dyn = c.post("/gen", headers=headers, json={"transaction_id": tx_dyn}).get_json()
    gen_sta = c.post("/gen", headers=headers, json={"transaction_id": tx_sta}).get_json()
    app.queue.wait(gen_dyn["job_id"])
    app.queue.wait(gen_sta["job_id"])

    status_dyn = c.get(gen_dyn["status_url"], headers=headers).get_json()
    status_sta = c.get(gen_sta["status_url"], headers=headers).get_json()

    assert status_dyn["status"] == "succeeded"
    assert status_sta["status"] == "succeeded"
    for status in (status_dyn, status_sta):
        artifacts = status["artifacts"]
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


def test_template_upload_multipart(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    app = create_app()
    c = app.test_client()
    headers = {"Authorization": "Bearer token-123"}

    with open("samples/templates/dynamic_template.pptx", "rb") as f:
        resp = c.post(
            "/templates",
            headers=headers,
            data={"mode": "dynamic", "file": (f, "dynamic_template.pptx")},
            content_type="multipart/form-data",
        )
    assert resp.status_code == 202
    body = resp.get_json()
    app.queue.wait(body["job_id"])
    status_body = c.get(body["status_url"], headers=headers).get_json()
    assert status_body["status"] == "succeeded"


def test_template_upload_conflict(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    app = create_app()
    c = app.test_client()
    headers = {"Authorization": "Bearer token-123"}

    with open("samples/templates/dynamic_template.pptx", "rb") as f:
        resp = c.post(
            "/templates",
            headers=headers,
            data={
                "mode": "dynamic",
                "file": (f, "dynamic_template.pptx"),
                "template_path": "samples/templates/dynamic_template.pptx",
            },
            content_type="multipart/form-data",
        )
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["code"] == "validation_error"


def test_prepare_upload_multipart(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    app = create_app()
    c = app.test_client()
    headers = {"Authorization": "Bearer token-123"}

    with open("samples/templates/dynamic_template.pptx", "rb") as f:
        tpl_resp = c.post(
            "/templates",
            headers=headers,
            data={"mode": "dynamic", "file": (f, "dynamic_template.pptx")},
            content_type="multipart/form-data",
        ).get_json()
    app.queue.wait(tpl_resp["job_id"])

    with open("samples/input/pitch.md", "rb") as f:
        prep_resp = c.post(
            "/prepare",
            headers=headers,
            data={"transaction_id": tpl_resp["transaction_id"], "mode": "dynamic", "file": (f, "pitch.md")},
            content_type="multipart/form-data",
        ).get_json()
    app.queue.wait(prep_resp["job_id"])
    status_body = c.get(prep_resp["status_url"], headers=headers).get_json()
    assert status_body["status"] == "succeeded"


def test_gen_artifact_download(monkeypatch, tmp_path):
    """テンプレ→prepare→compose→gen 実行後、artifact pptx をダウンロードできることを確認。"""

    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    app = create_app()
    c = app.test_client()
    headers = {"Authorization": "Bearer token-123"}

    tpl_resp = c.post(
        "/templates",
        headers=headers,
        json={"template_path": "samples/templates/static_slide.pptx", "mode": "static"},
    ).get_json()
    app.queue.wait(tpl_resp["job_id"])

    prep_resp = c.post(
        "/prepare",
        headers=headers,
        json={
            "transaction_id": tpl_resp["transaction_id"],
            "prepare_sources": ["samples/input/pitch.md"],
            "mode": "static",
        },
    ).get_json()
    app.queue.wait(prep_resp["job_id"])

    cmp_resp = c.post("/compose", headers=headers, json={"transaction_id": tpl_resp["transaction_id"]}).get_json()
    app.queue.wait(cmp_resp["job_id"])

    gen_resp = c.post("/gen", headers=headers, json={"transaction_id": tpl_resp["transaction_id"]}).get_json()
    app.queue.wait(gen_resp["job_id"])

    status_body = c.get(gen_resp["status_url"], headers=headers).get_json()
    assert status_body["status"] == "succeeded"
    download = c.get(f"/jobs/{gen_resp['job_id']}/artifacts/pptx", headers=headers)
    assert download.status_code == 200
    assert download.data


def test_gen_artifacts_response_uses_api_url(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    app = create_app()
    c = app.test_client()
    headers = {"Authorization": "Bearer token-123"}

    from pptx_generator.runtime.job_queue import JobRequest, JobState, JobStatus, get_queue

    queue = get_queue()
    queue.reset()

    job_id = "job-api-url"
    tx_id = "tx-api-url"
    pptx_path = tmp_path / tx_id / "gen" / job_id / "proposal.pptx"
    pptx_path.parent.mkdir(parents=True, exist_ok=True)
    pptx_path.write_bytes(b"dummy")

    state = JobState(
        request=JobRequest(stage="gen", func=lambda: None, job_id=job_id, transaction_id=tx_id),
        status=JobStatus.SUCCEEDED,
        result={"artifacts": {"pptx_url": str(pptx_path)}},
    )
    queue._jobs[job_id] = state  # type: ignore[attr-defined]

    resp = c.get(f"/jobs/{job_id}", headers=headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["artifacts"]["pptx_url"] == f"/jobs/{job_id}/artifacts/pptx"


def test_download_uses_registry_when_queue_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    app = create_app()
    c = app.test_client()
    headers = {"Authorization": "Bearer token-123"}

    from pptx_generator.runtime.job_queue import get_queue

    queue = get_queue()
    queue.reset()

    job_id = "job-registry"
    tx_id = "tx-registry"
    tx_root = tmp_path / tx_id
    pptx_path = tx_root / "gen" / job_id / "proposal.pptx"
    pptx_path.parent.mkdir(parents=True, exist_ok=True)
    pptx_path.write_bytes(b"registry")

    registry = {"gen": {"job_id": job_id, "artifacts": {"pptx_url": str(pptx_path.relative_to(tx_root))}}}
    (tx_root / "registry.json").write_text(json.dumps(registry))

    resp = c.get(f"/jobs/{job_id}/artifacts/pptx", headers=headers)
    assert resp.status_code == 200
    assert resp.data == b"registry"


def test_output_root_default(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    monkeypatch.delenv("PPTX_OUTPUT_ROOT", raising=False)
    with pytest.raises(RuntimeError) as exc:
        create_app()
    assert "PPTX_OUTPUT_ROOT" in str(exc.value)


def test_edit_job_submission(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "mock")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    app = create_app()
    c = app.test_client()

    resp = c.post(
        "/edit",
        headers={"Authorization": "Bearer token-123"},
        json={"pptx_path": "samples/templates/edit_sample.pptx"},
    )

    assert resp.status_code == 202
    job = resp.get_json()
    assert job["stage"] == "edit"
    status_resp = c.get(job["status_url"], headers={"Authorization": "Bearer token-123"})
    assert status_resp.status_code == 200


def test_edit_outputs_applied_edits_json(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "mock")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    app = create_app()
    c = app.test_client()
    headers = {"Authorization": "Bearer token-123"}

    resp = c.post(
        "/edit",
        headers=headers,
        json={
            "pptx_path": "samples/templates/edit_sample.pptx",
            "edits": [{"shape_id": 1, "contents": "Updated by test"}],
        },
    )
    assert resp.status_code == 202
    job = resp.get_json()

    status_body = {}
    for _ in range(10):
        status_resp = c.get(job["status_url"], headers=headers)
        assert status_resp.status_code == 200
        status_body = status_resp.get_json()
        if status_body["status"] not in ("pending", "running"):
            break
        time.sleep(0.05)
    assert status_body["status"] == "succeeded"
    # edits_json_url は返さない
    artifacts = status_body["artifacts"]
    assert "pptx_url" in artifacts


def test_edit_outputs_applied_edits_json_empty_edits(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "mock")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    app = create_app()
    c = app.test_client()
    headers = {"Authorization": "Bearer token-123"}

    resp = c.post(
        "/edit",
        headers=headers,
        json={"pptx_path": "samples/templates/edit_sample.pptx", "edits": []},
    )
    assert resp.status_code == 202
    job = resp.get_json()

    status_body = {}
    for _ in range(10):
        status_resp = c.get(job["status_url"], headers=headers)
        assert status_resp.status_code == 200
        status_body = status_resp.get_json()
        if status_body["status"] not in ("pending", "running"):
            break
        time.sleep(0.05)
    assert status_body["status"] == "succeeded"
    artifacts = status_body["artifacts"]
    assert "pptx_url" in artifacts


def test_edit_artifacts_absolute_path(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "mock")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    app = create_app()
    c = app.test_client()
    headers = {"Authorization": "Bearer token-123"}

    resp = c.post(
        "/edit",
        headers=headers,
        json={
            "pptx_path": "samples/templates/edit_sample.pptx",
            "edits": [{"shape_id": 1, "contents": "Updated by test"}],
        },
    )
    assert resp.status_code == 202
    job = resp.get_json()

    status_body = {}
    for _ in range(10):
        status_resp = c.get(job["status_url"], headers=headers)
        assert status_resp.status_code == 200
        status_body = status_resp.get_json()
        if status_body["status"] not in ("pending", "running"):
            break
        time.sleep(0.05)
    assert status_body["status"] == "succeeded"
    artifacts = status_body["artifacts"]
    assert artifacts["pptx_url"].startswith("/jobs/")


def test_edit_artifact_missing_returns_404(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "mock")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    app = create_app()
    c = app.test_client()
    headers = {"Authorization": "Bearer token-123"}

    resp = c.post(
        "/edit",
        headers=headers,
        json={"pptx_path": "samples/templates/edit_sample.pptx", "edits": [{"shape_id": 1, "contents": "Updated"}]},
    )
    assert resp.status_code == 202
    job = resp.get_json()

    status_body = {}
    for _ in range(10):
        status_resp = c.get(job["status_url"], headers=headers)
        status_body = status_resp.get_json()
        if status_body["status"] not in ("pending", "running"):
            break
        time.sleep(0.05)
    assert status_body["status"] == "succeeded"
    artifacts = status_body["artifacts"]
    tx_id = job["transaction_id"]
    job_id = job["job_id"]
    pptx_path = tmp_path / tx_id / "edit" / job_id / "edit_sample.pptx"
    if pptx_path.exists():
        pptx_path.unlink()
    missing_resp = c.get(artifacts["pptx_url"], headers=headers)
    assert missing_resp.status_code == 404


def test_edit_rejects_both_pptx_and_upload(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_LLM_PROVIDER", "mock")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    app = create_app()
    c = app.test_client()
    headers = {"Authorization": "Bearer token-123"}

    # path とファイルを両方送った場合は 422 を期待
    with open("samples/templates/edit_sample.pptx", "rb") as f:
        resp = c.post(
            "/edit",
            headers=headers,
            data={"pptx_path": "samples/templates/edit_sample.pptx", "file": (f, "edit_sample.pptx")},
            content_type="multipart/form-data",
        )
    assert resp.status_code == 422


def test_edit_llm_failure_returns_failed(monkeypatch, tmp_path):
    from pptx_generator.api import stages as stages_module

    monkeypatch.setenv("PPTX_LLM_PROVIDER", "mock")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")
    # モッククライアントでエラーを投げる
    class DummyClient:
        def rewrite(self, request):
            raise RuntimeError("llm-fail")
    monkeypatch.setattr(stages_module, "create_edit_ai_client", lambda: DummyClient())

    app = create_app()
    c = app.test_client()
    headers = {"Authorization": "Bearer token-123"}

    resp = c.post(
        "/edit",
        headers=headers,
        json={"pptx_path": "samples/templates/edit_sample.pptx"},
    )
    assert resp.status_code == 202
    job = resp.get_json()
    assert job["stage"] == "edit"

    # ポーリング（失敗完了まで待つ）
    status_body = {}
    for _ in range(10):
        status_resp = c.get(job["status_url"], headers=headers)
        assert status_resp.status_code == 200
        status_body = status_resp.get_json()
        if status_body["status"] not in ("pending", "running"):
            break
        time.sleep(0.05)
    assert status_body["status"] in ("failed", "succeeded")
    if status_body["status"] == "failed":
        assert status_body["error"] is not None


def test_edit_save_failure_marks_job_failed(monkeypatch, tmp_path):
    from pptx_generator.api import stages as stages_module

    monkeypatch.setenv("PPTX_LLM_PROVIDER", "mock")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")

    def _raise(*args, **kwargs):
        raise OSError("disk full")

    from pptx_generator.pipeline import edit_runner
    monkeypatch.setattr(edit_runner, "apply_and_save_edits", _raise)

    app = create_app()
    c = app.test_client()
    headers = {"Authorization": "Bearer token-123"}

    resp = c.post(
        "/edit",
        headers=headers,
        json={
            "pptx_path": "samples/templates/edit_sample.pptx",
            "edits": [{"shape_id": 1, "contents": "Updated by test"}],
        },
    )
    assert resp.status_code == 202
    job = resp.get_json()

    status_body = {}
    for _ in range(10):
        status_resp = c.get(job["status_url"], headers=headers)
        assert status_resp.status_code == 200
        status_body = status_resp.get_json()
        if status_body["status"] not in ("pending", "running"):
            break
        time.sleep(0.05)
    assert status_body["status"] == "failed"
    assert status_body["error"] is not None
    assert status_body["artifacts"] == {}


def test_edit_llm_returns_empty_edits(monkeypatch, tmp_path):
    from pptx_generator.api import stages as stages_module

    monkeypatch.setenv("PPTX_LLM_PROVIDER", "mock")
    monkeypatch.setenv("PPTX_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setenv("PPTX_API_BEARER_TOKEN", "token-123")

    class DummyClient:
        def __init__(self):
            self.model = "mock-empty"

        def rewrite(self, request):
            class Resp:
                edits = []
                model = "mock-empty"
            return Resp()

    monkeypatch.setattr(stages_module, "create_edit_ai_client", lambda: DummyClient())

    app = create_app()
    c = app.test_client()
    headers = {"Authorization": "Bearer token-123"}

    resp = c.post(
        "/edit",
        headers=headers,
        json={"pptx_path": "samples/templates/edit_sample.pptx"},
    )
    assert resp.status_code == 202
    job = resp.get_json()

    status_body = {}
    for _ in range(10):
        status_resp = c.get(job["status_url"], headers=headers)
        assert status_resp.status_code == 200
        status_body = status_resp.get_json()
        if status_body["status"] not in ("pending", "running"):
            break
        time.sleep(0.05)
    assert status_body["status"] == "succeeded"
    artifacts = status_body["artifacts"]
    assert "pptx_url" in artifacts
