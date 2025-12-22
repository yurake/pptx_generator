from __future__ import annotations

import logging
import hashlib
import hmac
import os
import time
import uuid
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Iterable, Optional

from flask import Blueprint, Flask, abort, g, jsonify, request, send_file

from pptx_generator.cli_handlers.template_commands import TemplateCommandConfig, run_template_command
from pptx_generator.cli_handlers.compose import ComposeCommandConfig, ComposeCommandError, run_compose_command
from pptx_generator.cli_handlers.prepare import PrepareCommandConfig, run_prepare_command, PrepareCommandError
from pptx_generator.cli_handlers.rendering import GenerateCommandConfig, GenerateCommandError, run_generate_command
from pptx_generator.runtime.job_queue import (
    JobRequest,
    JobStatus,
    InProcessJobQueue,
    get_queue,
)

def create_app() -> Flask:
    """Create Flask application for stage1-4 API."""

    app = Flask(__name__)
    _configure_logging(app)
    app.config["HMAC_KEYS"] = _load_hmac_keys()
    app.config["HMAC_SKEW_SEC"] = int(os.environ.get("PPTX_API_HMAC_CLOCK_SKEW_SEC", "300"))
    app.config["BEARER_TOKEN"] = os.environ.get("PPTX_API_BEARER_TOKEN")
    app.config["WORKER_COUNT"] = int(os.environ.get("PPTX_API_WORKERS", "1"))
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("PPTX_API_MAX_BODY", str(10 * 1024 * 1024)))
    app.queue = get_queue()  # type: ignore[attr-defined]
    app.queue.ensure_workers(app.config["WORKER_COUNT"])

    @app.before_request
    def _authenticate() -> Optional[tuple]:
        g.request_id = request.headers.get("X-Request-ID") or _generate_id("req")
        app.logger.info(
            "request start method=%s path=%s request_id=%s",
            request.method,
            request.path,
            g.request_id,
        )
        error = _verify_auth(
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
            getattr(g, "request_id", None),
        )
        response.headers.setdefault("X-Request-ID", getattr(g, "request_id", ""))
        return response

    api = Blueprint("api", __name__)

    @app.errorhandler(413)
    def handle_request_entity_too_large(e):
        return _error_response(413, "too_large", "request body too large")

    @api.errorhandler(PrepareCommandError)
    @api.errorhandler(ComposeCommandError)
    @api.errorhandler(GenerateCommandError)
    def handle_command_error(exc):
        code = getattr(exc, "exit_code", 1)
        if code in (4, 6):  # ファイル関連/検証エラー
            return _error_response(422, "validation_error", str(exc))
        return _error_response(500, "internal_error", str(exc))

    @api.post("/templates")
    def post_templates():
        payload = _require_json()
        _require_fields(payload, ["template_path"])
        tx_id = payload.get("transaction_id") or _generate_id("tx")
        job_id = _generate_id("tpl")
        state = _enqueue_job(app.queue, stage="template", job_id=job_id, transaction_id=tx_id, payload=payload)
        return _job_response(state)

    @api.post("/prepare")
    def post_prepare():
        payload = _require_json()
        tx_id = payload.get("transaction_id") or _generate_id("tx")
        job_id = _generate_id("prep")
        state = _enqueue_job(app.queue, stage="prepare", job_id=job_id, transaction_id=tx_id, payload=payload)
        return _job_response(state)

    @api.post("/compose")
    def post_compose():
        payload = _require_json()
        tx_id = payload.get("transaction_id") or _generate_id("tx")
        job_id = _generate_id("cmp")
        state = _enqueue_job(app.queue, stage="compose", job_id=job_id, transaction_id=tx_id, payload=payload)
        return _job_response(state)

    @api.post("/gen")
    def post_gen():
        payload = _require_json()
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
        state = app.queue.get_job(job_id)  # type: ignore[attr-defined]
        if state is None:
            return _error_response(404, "not_found", "job not found")
        if not isinstance(state.result, dict):
            return _error_response(404, "not_found", f"{artifact_type} not available")
        artifacts = state.result.get("artifacts") or {}
        path = artifacts.get(f"{artifact_type}_url")
        if not path:
            return _error_response(404, "not_found", f"{artifact_type} not available")
        file_path = Path(path)
        if not file_path.exists():
            return _error_response(404, "not_found", f"{artifact_type} not found")
        if artifact_type == "pptx":
            mimetype = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        elif artifact_type == "pdf":
            mimetype = "application/pdf"
        else:
            return _error_response(404, "not_found", f"{artifact_type} not available")
        return send_file(file_path, mimetype=mimetype, as_attachment=True, download_name=file_path.name)

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


def _configure_logging(app: Flask) -> None:
    logger = logging.getLogger("pptx_generator.api")
    level_name = os.environ.get("PPTX_API_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)

    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        log_path = Path("logs") / "out.log"
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(log_path, maxBytes=10 * 1024 * 1024, backupCount=5)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError:
            logger.warning("log file handler setup failed; continuing with stdout only")

    app.logger.handlers = logger.handlers  # type: ignore[assignment]
    app.logger.setLevel(level)
    app.logger.propagate = False
    app.config["API_LOGGER"] = logger


def _require_json() -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        resp = jsonify({"code": "bad_request", "message": "invalid json payload"})
        resp.status_code = 400
        abort(resp)
    return payload


def _require_fields(payload: dict, fields: Iterable[str]) -> None:
    missing = [field for field in fields if payload.get(field) in (None, "")]
    if missing:
        resp = jsonify({"code": "validation_error", "message": f"{', '.join(missing)} is required"})
        resp.status_code = 422
        abort(resp)


def _enqueue_job(queue: InProcessJobQueue, *, stage: str, job_id: str, transaction_id: str, payload: dict):
    output_root = _require_output_root()
    tx_root = Path(output_root) / transaction_id
    tx_root.mkdir(parents=True, exist_ok=True)
    template_artifacts = None
    prepare_artifacts = None
    compose_artifacts = None

    if stage == "template":
        workdir = _resolve_output_root(transaction_id, stage, job_id)

        def _run_template():
            if "template_path" not in payload:
                abort(_error_response(422, "validation_error", "template_path is required"))
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
    elif stage == "prepare":
        template_artifacts = _resolve_stage_artifacts(tx_root, "template", ["jobspec_url"])
        workdir = _resolve_output_root(transaction_id, stage, job_id)

        def _run_prepare():
            config = PrepareCommandConfig(
                prepare_paths=[Path(p) for p in payload.get("prepare_sources", [])],
                prepare_base_path=None,
                jobspec_path=Path(template_artifacts["jobspec_url"]),
                output_dir=Path(workdir),
                mode=payload.get("mode", "dynamic"),
                page_limit=payload.get("page_limit"),
                story_outline_path=None,
                page_offset=None,
                template_ai_policy=None,
                disable_template_ai=False,
                blueprint_override=None,
                metadata=None,
                analysis_summary=None,
                layout_filter=None,
            )
            result = run_prepare_command(config)
            artifacts = {
                "prepare_card_url": str(Path(workdir) / "prepare_card.json"),
                "prepare_log_url": str(Path(workdir) / "prepare_log.json"),
                "prepare_ai_log_url": str(Path(workdir) / "prepare_ai_log.json"),
                "ai_generation_meta_url": str(Path(workdir) / "ai_generation_meta.json"),
                "audit_log_url": str(Path(workdir) / "audit_log.json"),
            }
            return {"artifacts": artifacts, "result": result}

        func = _run_prepare
    elif stage == "compose":
        prepare_artifacts = _resolve_stage_artifacts(tx_root, "prepare", ["prepare_card_url"])
        template_artifacts = _resolve_stage_artifacts(tx_root, "template", ["jobspec_url"])
        workdir = _resolve_output_root(transaction_id, stage, job_id)
        generate_ready_path = Path(workdir) / "generate_ready.json"
        generate_ready_meta_path = Path(workdir) / "generate_ready_meta.json"
        draft_log = Path(workdir) / "draft_mapping_log.json"
        review_log = Path(workdir) / "draft_review_log.json"

        def _run_compose():
            config = ComposeCommandConfig(
                spec_path=Path(template_artifacts["jobspec_url"]),
                draft_output=Path(workdir) / "draft.json",
                target_length=None,
                structure_pattern=None,
                appendix_limit=10,
                analysis_summary_path=None,
                show_layout_reasons=bool(payload.get("show_layout_reasons", False)),
                output_dir=Path(workdir),
                rules_path=Path(payload.get("rules_path", ".pptx/template/diagnostics.json")),
                prepare_cards=Path(prepare_artifacts["prepare_card_url"]),
                draft_filename=str(draft_log.name),
                approved_filename=str(review_log.name),
                log_filename=str(draft_log.name),
                meta_filename=str(review_log.name),
                generate_ready_filename=str(generate_ready_path.name),
                generate_ready_meta_filename=str(generate_ready_meta_path.name),
            )
            result = run_compose_command(config)
            artifacts = {
                "generate_ready_url": str(generate_ready_path),
                "generate_ready_meta_url": str(generate_ready_meta_path),
                "draft_mapping_log_url": str(draft_log),
                "draft_review_log_url": str(review_log),
            }
            return {"artifacts": artifacts, "result": result}

        func = _run_compose
    elif stage == "gen":
        compose_artifacts = _resolve_stage_artifacts(tx_root, "compose", ["generate_ready_url"])
        workdir = _resolve_output_root(transaction_id, stage, job_id)
        pptx_path = Path(workdir) / "proposal.pptx"
        pdf_path = Path(workdir) / "proposal.pdf"

        def _run_gen():
            config = GenerateCommandConfig(
                generate_ready_path=Path(compose_artifacts["generate_ready_url"]),
                output_dir=Path(workdir),
                pptx_name=pptx_path.name,
                rules_path=Path(payload.get("rules_path", ".pptx/template/diagnostics.json")),
                export_pdf=bool(payload.get("export_pdf", False)),
                pdf_mode=payload.get("pdf_mode", "default"),
                pdf_output=str(pdf_path),
                libreoffice_path=None,
                pdf_timeout=payload.get("pdf_timeout", 120),
                pdf_retries=payload.get("pdf_retries", 1),
                polisher_toggle=None,
                polisher_path=None,
                polisher_rules=None,
                polisher_timeout=None,
                polisher_args=(),
                polisher_cwd=None,
                emit_structure_snapshot=bool(payload.get("emit_structure_snapshot", False)),
            )
            result = run_generate_command(config)
            artifacts = {
                "pptx_url": str(pptx_path),
            }
            if payload.get("export_pdf"):
                artifacts["pdf_url"] = str(pdf_path)
            return {"artifacts": artifacts, "result": result}

        func = _run_gen
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
    logging.getLogger("pptx_generator.api").info(
        "job enqueued stage=%s job_id=%s transaction_id=%s", stage, job_id, transaction_id
    )
    state = queue.enqueue(request)
    queue.ensure_workers(1)
    state = queue.wait(job_id)
    if stage in ("template", "prepare", "compose", "gen"):
        _update_registry(tx_root, stage, state)
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
    base = _require_output_root()
    return str(Path(base) / transaction_id / stage / job_id)


def _require_output_root() -> str:
    base = os.environ.get("PPTX_OUTPUT_ROOT")
    if not base:
        resp = jsonify({"code": "validation_error", "message": "PPTX_OUTPUT_ROOT is required"})
        resp.status_code = 422
        abort(resp)
    return base


def _registry_path(tx_root: Path) -> Path:
    return tx_root / "registry.json"


def _load_registry(tx_root: Path) -> Optional[dict]:
    path = _registry_path(tx_root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _update_registry(tx_root: Path, stage: str, state) -> None:
    registry = _load_registry(tx_root) or {}
    artifacts = {}
    if isinstance(state.result, dict):
        artifacts = state.result.get("artifacts") or {}
    # store relative paths when under tx_root
    rel_artifacts = {}
    for key, value in artifacts.items():
        p = Path(value)
        try:
            rel = p.relative_to(tx_root)
            rel_artifacts[key] = str(rel)
        except ValueError:
            rel_artifacts[key] = value
    registry[stage] = {"job_id": state.request.job_id, "artifacts": rel_artifacts}
    tx_root.mkdir(parents=True, exist_ok=True)
    _registry_path(tx_root).write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")


def _resolve_stage_artifacts(tx_root: Path, stage: str, keys: list[str]) -> dict[str, str]:
    registry = _load_registry(tx_root)
    if registry is None:
        resp = jsonify({"code": "not_found", "message": "transaction not found"})
        resp.status_code = 404
        abort(resp)
    entry = registry.get(stage)
    if not entry or "artifacts" not in entry:
        resp = jsonify({"code": "validation_error", "message": f"{stage} artifacts not found"})
        resp.status_code = 422
        abort(resp)
    artifacts = entry["artifacts"]
    resolved = {}
    for key in keys:
        path = artifacts.get(key)
        if not path:
            resp = jsonify({"code": "validation_error", "message": f"{stage} artifacts not found"})
            resp.status_code = 422
            abort(resp)
        resolved[key] = str((tx_root / path).resolve())
    return resolved
