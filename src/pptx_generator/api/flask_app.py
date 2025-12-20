from __future__ import annotations

import hashlib
import hmac
import os
import time
import uuid
from typing import Iterable, Optional

from flask import Blueprint, Flask, abort, g, jsonify, request


def create_app() -> Flask:
    """Create Flask application for stage1-4 API."""

    app = Flask(__name__)
    app.config["HMAC_KEYS"] = _load_hmac_keys()
    app.config["HMAC_SKEW_SEC"] = int(os.environ.get("PPTX_API_HMAC_CLOCK_SKEW_SEC", "300"))
    app.config["BEARER_TOKEN"] = os.environ.get("PPTX_API_BEARER_TOKEN")

    @app.before_request
    def _authenticate() -> Optional[tuple]:
        error = _verify_auth(
            bearer_token=app.config["BEARER_TOKEN"],
            hmac_keys=app.config["HMAC_KEYS"],
            skew_sec=app.config["HMAC_SKEW_SEC"],
        )
        if error is not None:
            return error
        return None

    api = Blueprint("api", __name__)

    @api.post("/templates")
    def post_templates():
        payload = request.get_json(silent=True) or {}
        tx_id = payload.get("transaction_id") or _generate_id("tx")
        job_id = _generate_id("tpl")
        return _job_response(job_id, tx_id, "template")

    @api.post("/prepare")
    def post_prepare():
        payload = request.get_json(silent=True) or {}
        tx_id = payload.get("transaction_id") or _generate_id("tx")
        job_id = _generate_id("prep")
        return _job_response(job_id, tx_id, "prepare")

    @api.post("/compose")
    def post_compose():
        payload = request.get_json(silent=True) or {}
        tx_id = payload.get("transaction_id") or _generate_id("tx")
        job_id = _generate_id("cmp")
        return _job_response(job_id, tx_id, "compose")

    @api.post("/gen")
    def post_gen():
        payload = request.get_json(silent=True) or {}
        tx_id = payload.get("transaction_id") or _generate_id("tx")
        job_id = _generate_id("gen")
        return _job_response(job_id, tx_id, "gen")

    @api.get("/jobs/<job_id>")
    def get_job(job_id: str):
        tx_id = request.args.get("transaction_id") or _generate_id("tx")
        body = {
            "job_id": job_id,
            "transaction_id": tx_id,
            "status": "pending",
            "stage": "unknown",
            "status_url": f"/jobs/{job_id}",
            "transaction_url": f"/transactions/{tx_id}",
        }
        return jsonify(body)

    @api.get("/transactions/<transaction_id>")
    def get_transaction(transaction_id: str):
        body = {
            "transaction_id": transaction_id,
            "jobs": [],
        }
        return jsonify(body)

    @api.get("/jobs/<job_id>/artifacts/<artifact_type>")
    def get_artifact(job_id: str, artifact_type: str):
        return _error_response(404, "not_found", f"{artifact_type} not available for {job_id}")

    app.register_blueprint(api)
    return app


def _load_hmac_keys() -> list[str]:
    keys: list[str] = []
    current = os.environ.get("PPTX_API_HMAC_KEY_CURRENT")
    if current:
        keys.append(current)
    next_key = os.environ.get("PPTX_API_HMAC_KEY_NEXT")
    if next_key:
        keys.append(next_key)
    return keys


def _verify_auth(bearer_token: Optional[str], hmac_keys: Iterable[str], skew_sec: int) -> Optional[tuple]:
    auth_header = request.headers.get("Authorization")
    if bearer_token and auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        if hmac.compare_digest(token, bearer_token):
            g.auth_scheme = "bearer"
            return None
    sig = request.headers.get("X-Signature")
    ts = request.headers.get("X-Timestamp")
    if sig and ts and list(hmac_keys):
        now = int(time.time())
        try:
            ts_int = int(ts)
        except ValueError:
            return _error_response(401, "unauthorized", "invalid timestamp")
        if abs(now - ts_int) > skew_sec:
            return _error_response(401, "unauthorized", "timestamp skew too large")
        body_hash = hashlib.sha256(request.get_data(cache=True)).hexdigest()
        signing_str = f"{ts}\n{request.method}\n{request.path}\n{body_hash}"
        for key in hmac_keys:
            expected = hmac.new(key.encode(), signing_str.encode(), hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected, sig):
                g.auth_scheme = "hmac"
                return None
        return _error_response(401, "unauthorized", "signature mismatch")
    return _error_response(401, "unauthorized", "missing auth")


def _error_response(status_code: int, code: str, message: str):
    return jsonify({"code": code, "message": message}), status_code


def _job_response(job_id: str, transaction_id: str, stage: str):
    body = {
        "job_id": job_id,
        "transaction_id": transaction_id,
        "status": "pending",
        "stage": stage,
        "status_url": f"/jobs/{job_id}",
        "transaction_url": f"/transactions/{transaction_id}",
    }
    return jsonify(body), 202


def _generate_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"
