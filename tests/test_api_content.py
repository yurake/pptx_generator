"""Content approval API tests."""

from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi.testclient import TestClient

from pptx_generator.api import create_app
from pptx_generator.api.store import ContentStore


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    store = ContentStore(base_dir=tmp_path / "store")
    monkeypatch.setenv("CONTENT_API_TOKEN", "test-token")
    app = create_app(store)
    return TestClient(app)


def _auth_headers(etag: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": "Bearer test-token",
        "X-Actor": "tester@example.com",
        "X-Request-ID": "req-1",
    }
    if etag:
        headers["If-Match"] = etag
    return headers


def test_create_update_approve_flow(client: TestClient) -> None:
    # Create cards
    payload = {
        "spec_id": "job-001",
        "cards": [
            {
                "slide_id": "agenda",
                "title": "アジェンダ",
                "body": ["背景整理", "提案サマリー"],
                "table_data": {
                    "headers": ["項目", "値"],
                    "rows": [["A", "1"]],
                },
                "note": "メモ",
                "intent": "outline",
                "story": {"phase": "intro", "chapter_id": "ch-01", "angle": "背景"},
            }
        ],
    }
    response = client.post("/v1/content/cards", json=payload, headers=_auth_headers())
    assert response.status_code == 201
    etag = response.headers["ETag"]

    # Update card
    update_payload = {
        "title": "アジェンダ（更新）",
        "body": ["背景整理（承認済み）", "提案サマリー（承認済み）"],
        "autofix_applied": ["p-agenda-bullet"],
    }
    response = client.patch(
        "/v1/content/cards/agenda",
        params={"spec_id": "job-001"},
        json=update_payload,
        headers=_auth_headers(etag),
    )
    assert response.status_code == 200
    etag = response.headers["ETag"]
    revision_payload = response.json()
    assert revision_payload["content_hash"].startswith("sha256:")

    # Approve card (idempotent)
    approve_payload = {"notes": "承認", "applied_autofix": ["p01"]}
    response = client.post(
        "/v1/content/cards/agenda/approve",
        params={"spec_id": "job-001"},
        json=approve_payload,
        headers=_auth_headers(etag),
    )
    assert response.status_code == 200
    etag = response.headers["ETag"]
    approve_body = response.json()
    assert approve_body["status"] == "approved"

    # Fetch card
    response = client.get(
        "/v1/content/cards/agenda",
        params={"spec_id": "job-001"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    card = response.json()
    assert card["title"] == "アジェンダ（更新）"
    assert card["history"][-1]["action"] == "approve"
    assert response.headers["ETag"] == etag

    # List logs
    response = client.get(
        "/v1/content/logs",
        params={"spec_id": "job-001"},
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    logs = response.json()
    assert len(logs["items"]) >= 2
    actions = {item["action"] for item in logs["items"]}
    assert {"update", "approve"}.issubset(actions)


def test_requires_token_when_configured(tmp_path, monkeypatch) -> None:
    store = ContentStore(base_dir=tmp_path / "store")
    monkeypatch.setenv("CONTENT_API_TOKEN", "token")
    app = create_app(store)
    unauthenticated_client = TestClient(app)

    response = unauthenticated_client.post(
        "/v1/content/cards",
        json={
            "spec_id": "job-unauth",
            "cards": [
                {
                    "slide_id": "cover",
                    "title": "Cover",
                    "body": [],
                }
            ],
        },
    )
    assert response.status_code == 401
