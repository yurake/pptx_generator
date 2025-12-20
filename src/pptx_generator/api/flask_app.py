from __future__ import annotations

import hashlib
import hmac
import os
import time
import uuid
from pathlib import Path
from typing import Iterable, Optional

from flask import Blueprint, Flask, abort, g, jsonify, request

from pptx_generator.cli_handlers.template_commands import TemplateCommandConfig, run_template_command
from pptx_generator.runtime.job_queue import (
    JobRequest,
    JobStatus,
    InProcessJobQueue,
    get_queue,
)

def create_app() -> Flask:
    """Create Flask application for stage1-4 API."""

    app = Flask(__name__)
    app.config["HMAC_KEYS"] = _load_hmac_keys()
    app.config["HMAC_SKEW_SEC"] = int(os.environ.get("PPTX_API_HMAC_CLOCK_SKEW_SEC", "300"))
    app.config["BEARER_TOKEN"] = os.environ.get("PPTX_API_BEARER_TOKEN")
    app.config["WORKER_COUNT"] = int(os.environ.get("PPTX_API_WORKERS", "1"))
    app.queue = get_queue()  # type: ignore[attr-defined]
    app.queue.ensure_workers(app.config["WORKER_COUNT"])

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
        state = _enqueue_job(app.queue, stage="template", job_id=job_id, transaction_id=tx_id, payload=payload)
        return _job_response(state)

    @api.post("/prepare")
    def post_prepare():
        payload = request.get_json(silent=True) or {}
        tx_id = payload.get("transaction_id") or _generate_id("tx")
        job_id = _generate_id("prep")
        state = _enqueue_job(app.queue, stage="prepare", job_id=job_id, transaction_id=tx_id, payload=payload)
        return _job_response(state)

    @api.post("/compose")
    def post_compose():
        payload = request.get_json(silent=True) or {}
        tx_id = payload.get("transaction_id") or _generate_id("tx")
        job_id = _generate_id("cmp")
        state = _enqueue_job(app.queue, stage="compose", job_id=job_id, transaction_id=tx_id, payload=payload)
        return _job_response(state)

    @api.post("/gen")
    def post_gen():
        payload = request.get_json(silent=True) or {}
        tx_id = payload.get("transaction_id") or _generate_id("tx")
        job_id = _generate_id("gen")
        state = _enqueue_job(app.queue, stage="gen", job_id=job_id, transaction_id=tx_id, payload=payload)
        return _job_response(state)

    @api.get("/jobs/<job_id>")
    def get_job(job_id: str):
        state = app.queue.get_job(job_id)  # type: ignore[attr-defined]
        if state is None:
            return _error_response(404, "not_found", "job not found")
        return jsonify(_job_status_body(state))

    @api.get("/transactions/<transaction_id>")
    def get_transaction(transaction_id: str):
        body = {
            "transaction_id": transaction_id,
            "jobs": _jobs_by_transaction(app.queue, transaction_id),  # type: ignore[attr-defined]
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


def _enqueue_job(queue: InProcessJobQueue, *, stage: str, job_id: str, transaction_id: str, payload: dict):
    if stage == "template":
        workdir = _resolve_output_root(transaction_id, stage, job_id)

        def _run_template():
            config = TemplateCommandConfig(
                template_path=Path(payload["template_path"]),
                output_dir=Path(workdir),
                format="json",
                layout=payload.get("layout"),
                anchor=payload.get("anchor"),
                layout_mode=payload.get("mode", "static"),
                static_source="template",
                template_ai_policy=None,
                template_ai_policy_id=None,
                disable_template_ai=False,
                with_release=bool(payload.get("with_release")),
                brand=payload.get("brand"),
                version=payload.get("version"),
                template_id=payload.get("template_id"),
                release_output=Path(workdir),
                generated_by=None,
                reviewed_by=None,
                baseline_release=None,
                golden_specs=(),
                slide_snapshot=bool(payload.get("slide_snapshot")),
                force=bool(payload.get("force")),
            )
            result = run_template_command(config)
            artifacts = {
                "jobspec_url": str(Path(workdir) / "jobspec.json"),
                "template_spec_url": str(Path(workdir) / "template_spec.json"),
            }
            return {"artifacts": artifacts, "result": result}

        func = _run_template
    else:
        def _noop_job():
            if stage == "gen":
                return {"artifacts": {"pptx_url": f"/jobs/{job_id}/artifacts/pptx"}}
            return {}

        func = _noop_job

    request = JobRequest(
        stage=stage,
        job_id=job_id,
        transaction_id=transaction_id,
        func=func,
    )
    state = queue.enqueue(request)
    queue.ensure_workers(1)
    return state


def _job_response(state):
    body = _job_status_body(state)
    return jsonify(body), 202


def _job_status_body(state):
    artifacts = {}
    if isinstance(state.result, dict):
        artifacts = state.result.get("artifacts") or {}
    return {
        "job_id": state.request.job_id,
        "transaction_id": state.request.transaction_id,
        "status": state.status,
        "stage": state.request.stage,
        "status_url": f"/jobs/{state.request.job_id}",
        "transaction_url": f"/transactions/{state.request.transaction_id}",
        "created_at": state.request.enqueued_at.isoformat(),
        "started_at": state.started_at.isoformat() if state.started_at else None,
        "finished_at": state.finished_at.isoformat() if state.finished_at else None,
        "artifacts": artifacts,
        "error": _error_info(state),
    }


def _error_info(state):
    if state.status != JobStatus.FAILED or state.error is None:
        return None
    return {"code": "job_failed", "message": str(state.error)}


def _jobs_by_transaction(queue: InProcessJobQueue, transaction_id: str):
    jobs = []
    for state in list(queue._jobs.values()):  # type: ignore[attr-defined]
        if state.request.transaction_id == transaction_id:
            jobs.append(_job_status_body(state))
    return jobs


def _generate_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _resolve_output_root(transaction_id: str, stage: str, job_id: str) -> str:
    base = os.environ.get("PPTX_OUTPUT_ROOT")
    if base:
        return str(Path(base) / transaction_id / stage / job_id)
    return str(Path(".pptx") / stage)
