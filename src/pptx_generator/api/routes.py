from __future__ import annotations

from typing import Optional

from flask import Blueprint, g, jsonify, request, send_file

from pptx_generator.api.auth import verify_auth
from pptx_generator.api.http import error_response
from pptx_generator.api.jobs import enqueue_job, generate_id, job_response, job_status_body, jobs_by_transaction
from pptx_generator.api.payloads import prepare_prepare_payload, prepare_template_payload
from pptx_generator.api.registry import ARTIFACT_KEYS, resolve_artifact_path
from pptx_generator.api.utils import parse_payload, require_json
from pptx_generator.api.stages import (
    TemplateCommandError,
    PrepareCommandError,
    ComposeCommandError,
    GenerateCommandError,
)
from pptx_generator.logging import set_current_request_id, reset_current_request_id
from pptx_generator.runtime.job_queue import get_queue


api_blueprint = Blueprint("api", __name__)


@api_blueprint.get("/health")
def get_health():
    return jsonify({"status": "ok"})


@api_blueprint.record_once
def setup_state(setup_state):
    app = setup_state.app

    @app.before_request
    def _authenticate() -> Optional[tuple]:
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.cookies:
            return error_response(401, "unauthorized", "cookie-based authentication is not allowed")
        g.request_id = request.headers.get("X-Request-ID") or generate_id("req")
        g._request_ctx_token = set_current_request_id(g.request_id)
        app.logger.info(
            "request start method=%s path=%s request_id=%s",
            request.method,
            request.path,
            (g.request_id or "")[:8],
        )
        if request.path == "/health":
            return None
        error = verify_auth(
            bearer_token=app.config["BEARER_TOKEN"],
            hmac_keys=app.config["HMAC_KEYS"],
            skew_sec=app.config["HMAC_SKEW_SEC"],
        )
        if error is not None:
            app.logger.warning(
                "auth failed method=%s path=%s request_id=%s",
                request.method,
                request.path,
                g.request_id,
            )
            return error
        return None

    @app.after_request
    def _log_response(response):
        app.logger.info(
            "request end method=%s path=%s status=%s request_id=%s",
            request.method,
            request.path,
            response.status_code,
            (getattr(g, "request_id", None) or "")[:8],
        )
        response.headers.setdefault("X-Request-ID", getattr(g, "request_id", ""))
        token = getattr(g, "_request_ctx_token", None)
        if token is not None:
            reset_current_request_id(token)
        return response


@api_blueprint.errorhandler(413)
def handle_request_entity_too_large(e):
    return error_response(413, "too_large", "request body too large")


@api_blueprint.errorhandler(PrepareCommandError)
@api_blueprint.errorhandler(ComposeCommandError)
@api_blueprint.errorhandler(GenerateCommandError)
def handle_command_error(exc):
    code = getattr(exc, "exit_code", 1)
    if code in (4, 6):  # ファイル関連/検証エラー
        return error_response(422, "validation_error", str(exc))
    return error_response(500, "internal_error", str(exc))


@api_blueprint.post("/templates")
def post_templates():
    payload = parse_payload(stage="template")
    tx_id = payload.get("transaction_id") or generate_id("tx")
    job_id = generate_id("tpl")
    state = enqueue_job(
        get_queue(),
        stage="template",
        job_id=job_id,
        transaction_id=tx_id,
        payload=payload,
        template_payload_builder=prepare_template_payload,
        prepare_payload_builder=prepare_prepare_payload,
    )
    return job_response(state)


@api_blueprint.post("/prepare")
def post_prepare():
    payload = parse_payload(stage="prepare")
    tx_id = payload.get("transaction_id") or generate_id("tx")
    job_id = generate_id("prep")
    state = enqueue_job(
        get_queue(),
        stage="prepare",
        job_id=job_id,
        transaction_id=tx_id,
        payload=payload,
        template_payload_builder=prepare_template_payload,
        prepare_payload_builder=prepare_prepare_payload,
    )
    return job_response(state)


@api_blueprint.post("/compose")
def post_compose():
    payload = require_json()
    tx_id = payload.get("transaction_id") or generate_id("tx")
    job_id = generate_id("cmp")
    state = enqueue_job(
        get_queue(),
        stage="compose",
        job_id=job_id,
        transaction_id=tx_id,
        payload=payload,
        template_payload_builder=prepare_template_payload,
        prepare_payload_builder=prepare_prepare_payload,
    )
    return job_response(state)


@api_blueprint.post("/gen")
def post_gen():
    payload = require_json()
    tx_id = payload.get("transaction_id") or generate_id("tx")
    job_id = generate_id("gen")
    state = enqueue_job(
        get_queue(),
        stage="gen",
        job_id=job_id,
        transaction_id=tx_id,
        payload=payload,
        template_payload_builder=prepare_template_payload,
        prepare_payload_builder=prepare_prepare_payload,
    )
    return job_response(state)




@api_blueprint.get("/jobs/<job_id>")
def get_job(job_id: str):
    state = get_queue().get_job(job_id)  # type: ignore[attr-defined]
    if state is None:
        return error_response(404, "not_found", "job not found")
    return jsonify(job_status_body(state))


@api_blueprint.get("/transactions/<transaction_id>")
def get_transaction(transaction_id: str):
    body = {
        "transaction_id": transaction_id,
        "jobs": jobs_by_transaction(get_queue(), transaction_id),  # type: ignore[attr-defined]
    }
    return jsonify(body)


@api_blueprint.get("/jobs/<job_id>/artifacts/<artifact_type>")
def get_artifact(job_id: str, artifact_type: str):
    if artifact_type not in ARTIFACT_KEYS:
        return error_response(404, "not_found", f"{artifact_type} not available")
    file_path = resolve_artifact_path(job_id, artifact_type)
    if not file_path:
        return error_response(404, "not_found", f"{artifact_type} not available")
    if not file_path.exists():
        return error_response(404, "not_found", f"{artifact_type} not found")
    if artifact_type == "pptx":
        mimetype = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    elif artifact_type == "pdf":
        mimetype = "application/pdf"
    else:
        return error_response(404, "not_found", f"{artifact_type} not available")
    return send_file(file_path, mimetype=mimetype, as_attachment=True, download_name=file_path.name)
