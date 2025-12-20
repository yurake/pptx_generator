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
