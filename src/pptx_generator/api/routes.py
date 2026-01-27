from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Optional

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None

try:
    import msvcrt
except ImportError:  # pragma: no cover - non-Windows
    msvcrt = None

from flask import Blueprint, abort, g, jsonify, request, send_file

from pptx_generator.api.utils import abort_error, parse_payload, require_json, require_fields, require_path_exists, save_uploaded_files
from pptx_generator.api.stages import (
    build_template_job,
    build_prepare_job,
    build_compose_job,
    build_gen_job,
    build_edit_job,
    TemplateCommandError,
    PrepareCommandError,
    ComposeCommandError,
    GenerateCommandError,
    EditCommandError,
)
from pptx_generator.logging import set_current_request_id, reset_current_request_id
from pptx_generator.runtime.job_queue import (
    JobRequest,
    JobStatus,
    JobState,
    InProcessJobQueue,
    get_queue,
)

ALLOWED_UPLOAD_EXT = {".pptx", ".md", ".txt", ".json"}
ARTIFACT_KEYS = {"pptx": "pptx_url", "pdf": "pdf_url"}


api_blueprint = Blueprint("api", __name__)


@api_blueprint.get("/health")
def get_health():
    return jsonify({"status": "ok"})


def _prepare_template_payload(tx_root: Path, payload: dict) -> dict:
    uploads = save_uploaded_files(tx_root, request.files.values(), ALLOWED_UPLOAD_EXT) if request.files else []
    if uploads and payload.get("template_path"):
        abort_error(422, "validation_error", "template_path and file cannot both be set")
    if len(uploads) > 1:
        abort_error(422, "validation_error", "only one template file is allowed")
    if uploads:
        payload["template_path"] = str(uploads[0])
    require_fields(payload, ["template_path"])
    require_path_exists(payload.get("template_path"), "template_path")
    return payload


def _prepare_prepare_payload(queue: InProcessJobQueue, tx_root: Path, transaction_id: str, payload: dict) -> dict:
    uploads = save_uploaded_files(tx_root, request.files.values(), ALLOWED_UPLOAD_EXT) if request.files else []
    sources = payload.get("prepare_sources") or []
    if isinstance(sources, str):
        sources = [sources]
    sources = list(sources) + [str(p) for p in uploads]
    if payload.get("prepare_path"):
        require_path_exists(payload["prepare_path"], "prepare_path")
    if not sources:
        abort_error(422, "validation_error", "prepare_sources is required")
    for src in sources:
        require_path_exists(src, "prepare_sources")
    payload["prepare_inputs"] = sources
    payload["mode"] = (payload.get("mode") or "dynamic").lower()
    return payload


def _prepare_edit_payload(tx_root: Path, payload: dict) -> dict:
    uploads = save_uploaded_files(tx_root, request.files.values(), {".pptx"}) if request.files else []
    if uploads and payload.get("pptx_path"):
        abort_error(422, "validation_error", "pptx_path and file cannot both be set")
    if len(uploads) > 1:
        abort_error(422, "validation_error", "only one pptx file is allowed")
    if uploads:
        payload["pptx_path"] = str(uploads[0])
    edits_value = payload.get("edits")
    if edits_value is not None and isinstance(edits_value, str):
        try:
            parsed = json.loads(edits_value)
        except json.JSONDecodeError as exc:
            abort_error(422, "validation_error", f"edits is not valid JSON: {exc}")
        if not isinstance(parsed, list):
            abort_error(422, "validation_error", "edits must be a JSON array")
        payload["edits"] = parsed
    require_fields(payload, ["pptx_path"])
    require_path_exists(payload.get("pptx_path"), "pptx_path")
    if payload.get("edits_json"):
        require_path_exists(payload.get("edits_json"), "edits_json")
    return payload


@api_blueprint.record_once
def setup_state(setup_state):
    app = setup_state.app

    @app.before_request
    def _authenticate() -> Optional[tuple]:
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.cookies:
            return _error_response(401, "unauthorized", "cookie-based authentication is not allowed")
        g.request_id = request.headers.get("X-Request-ID") or _generate_id("req")
        g._request_ctx_token = set_current_request_id(g.request_id)
        app.logger.info(
            "request start method=%s path=%s request_id=%s",
            request.method,
            request.path,
            (g.request_id or "")[:8],
        )
        if request.path == "/health":
            return None
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
            (getattr(g, "request_id", None) or "")[:8],
        )
        response.headers.setdefault("X-Request-ID", getattr(g, "request_id", ""))
        token = getattr(g, "_request_ctx_token", None)
        if token is not None:
            reset_current_request_id(token)
        return response


@api_blueprint.errorhandler(413)
def handle_request_entity_too_large(e):
    return _error_response(413, "too_large", "request body too large")


@api_blueprint.errorhandler(PrepareCommandError)
@api_blueprint.errorhandler(ComposeCommandError)
@api_blueprint.errorhandler(GenerateCommandError)
@api_blueprint.errorhandler(EditCommandError)
def handle_command_error(exc):
    code = getattr(exc, "exit_code", 1)
    if code in (4, 6):  # ファイル関連/検証エラー
        return _error_response(422, "validation_error", str(exc))
    return _error_response(500, "internal_error", str(exc))


@api_blueprint.post("/templates")
def post_templates():
    payload = parse_payload(stage="template")
    tx_id = payload.get("transaction_id") or _generate_id("tx")
    job_id = _generate_id("tpl")
    state = _enqueue_job(get_queue(), stage="template", job_id=job_id, transaction_id=tx_id, payload=payload)
    return _job_response(state)


@api_blueprint.post("/prepare")
def post_prepare():
    payload = parse_payload(stage="prepare")
    tx_id = payload.get("transaction_id") or _generate_id("tx")
    job_id = _generate_id("prep")
    state = _enqueue_job(get_queue(), stage="prepare", job_id=job_id, transaction_id=tx_id, payload=payload)
    return _job_response(state)


@api_blueprint.post("/compose")
def post_compose():
    payload = require_json()
    tx_id = payload.get("transaction_id") or _generate_id("tx")
    job_id = _generate_id("cmp")
    state = _enqueue_job(get_queue(), stage="compose", job_id=job_id, transaction_id=tx_id, payload=payload)
    return _job_response(state)


@api_blueprint.post("/gen")
def post_gen():
    payload = require_json()
    tx_id = payload.get("transaction_id") or _generate_id("tx")
    job_id = _generate_id("gen")
    state = _enqueue_job(get_queue(), stage="gen", job_id=job_id, transaction_id=tx_id, payload=payload)
    return _job_response(state)


@api_blueprint.post("/edit")
def post_edit():
    if request.mimetype and request.mimetype.startswith("multipart/"):
        data: dict = {}
        for key, values in request.form.lists():
            if len(values) == 1:
                data[key] = values[0]
            else:
                data[key] = values
        payload = data
    else:
        payload = require_json()
    tx_id = payload.get("transaction_id") or _generate_id("tx")
    job_id = _generate_id("edit")
    state = _enqueue_job(get_queue(), stage="edit", job_id=job_id, transaction_id=tx_id, payload=payload)
    return _job_response(state)


@api_blueprint.get("/jobs/<job_id>")
def get_job(job_id: str):
    state = get_queue().get_job(job_id)  # type: ignore[attr-defined]
    if state is None:
        return _error_response(404, "not_found", "job not found")
    return jsonify(_job_status_body(state))


@api_blueprint.get("/transactions/<transaction_id>")
def get_transaction(transaction_id: str):
    body = {
        "transaction_id": transaction_id,
        "jobs": _jobs_by_transaction(get_queue(), transaction_id),  # type: ignore[attr-defined]
    }
    return jsonify(body)


@api_blueprint.get("/jobs/<job_id>/artifacts/<artifact_type>")
def get_artifact(job_id: str, artifact_type: str):
    if artifact_type not in ARTIFACT_KEYS:
        return _error_response(404, "not_found", f"{artifact_type} not available")
    file_path = _resolve_artifact_path(job_id, artifact_type)
    if not file_path:
        return _error_response(404, "not_found", f"{artifact_type} not available")
    if not file_path.exists():
        return _error_response(404, "not_found", f"{artifact_type} not found")
    if artifact_type == "pptx":
        mimetype = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    elif artifact_type == "pdf":
        mimetype = "application/pdf"
    else:
        return _error_response(404, "not_found", f"{artifact_type} not available")
    return send_file(file_path, mimetype=mimetype, as_attachment=True, download_name=file_path.name)


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
    output_root = _require_output_root()
    tx_root = Path(output_root) / transaction_id
    tx_root.mkdir(parents=True, exist_ok=True)
    if stage == "template":
        func = build_template_job(
            payload=_prepare_template_payload(tx_root, payload),
            workdir=Path(_resolve_output_root(transaction_id, stage, job_id)),
        )
    elif stage == "prepare":
        func = build_prepare_job(
            payload=_prepare_prepare_payload(queue, tx_root, transaction_id, payload),
            workdir=Path(_resolve_output_root(transaction_id, stage, job_id)),
            jobspec_path=Path(_ensure_stage_artifacts(queue, tx_root, transaction_id, "template", ["jobspec_url"])["jobspec_url"]),
            tx_root=tx_root,
        )
    elif stage == "compose":
        func = build_compose_job(
            payload=payload,
            workdir=Path(_resolve_output_root(transaction_id, stage, job_id)),
            template_artifacts=_ensure_stage_artifacts(queue, tx_root, transaction_id, "template", ["jobspec_url", "diagnostics_url"]),
            prepare_artifacts=_ensure_stage_artifacts(queue, tx_root, transaction_id, "prepare", ["prepare_card_url"]),
        )
    elif stage == "gen":
        func = build_gen_job(
            payload=payload,
            workdir=Path(_resolve_output_root(transaction_id, stage, job_id)),
            compose_artifacts=_ensure_stage_artifacts(queue, tx_root, transaction_id, "compose", ["generate_ready_url"]),
            template_artifacts=_ensure_stage_artifacts(queue, tx_root, transaction_id, "template", ["diagnostics_url"], allow_missing=True),
        )
    elif stage == "edit":
        func = build_edit_job(
            payload=_prepare_edit_payload(tx_root, payload),
            workdir=Path(_resolve_output_root(transaction_id, stage, job_id)),
        )
    else:
        def _noop_job():
            if stage == "gen":
                return {"artifacts": {"pptx_url": f"/jobs/{job_id}/artifacts/pptx"}}
            return {}

        func = _noop_job

    job_request = JobRequest(
        stage=stage,
        job_id=job_id,
        transaction_id=transaction_id,
        func=_wrap_job(stage, job_id, transaction_id, func),
    )
    logging.getLogger("pptx_generator.api").info(
        "job enqueued stage=%s job_id=%s transaction_id=%s",
        _sanitize_for_log(stage),
        _sanitize_for_log(job_id),
        _sanitize_for_log(transaction_id),
    )
    state = queue.enqueue(job_request)
    queue.ensure_workers(1)
    return state


def _job_response(state):
    body = _job_status_body(state)
    return jsonify(body), 202


def _job_status_body(state):
    tx_root = _output_root() / state.request.transaction_id
    if state.status == JobStatus.SUCCEEDED:
        _update_registry(tx_root, state.request.stage, state)
    artifacts = {}
    if state.request.stage == "edit" and state.status == JobStatus.SUCCEEDED:
        artifacts["pptx_url"] = _artifact_api_path(state.request.job_id, "pptx")
    elif state.request.stage == "gen":
        for artifact_type in ARTIFACT_KEYS:
            path = _resolve_artifact_path(state.request.job_id, artifact_type, state=state, tx_root=tx_root)
            if path:
                artifacts[ARTIFACT_KEYS[artifact_type]] = _artifact_api_path(state.request.job_id, artifact_type)
    elif isinstance(state.result, dict):
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


def _artifact_api_path(job_id: str, artifact_type: str) -> str:
    return f"/jobs/{job_id}/artifacts/{artifact_type}"


def _normalize_artifact_path(tx_root: Path, path_value: str) -> Optional[Path]:
    path = Path(path_value)
    if path.is_absolute():
        return path.resolve()
    resolved = (tx_root / path).resolve()
    try:
        resolved.relative_to(tx_root)
    except ValueError:
        return None
    return resolved


def _artifact_path_from_state(state, tx_root: Path, artifact_type: str) -> Optional[Path]:
    if not isinstance(state.result, dict):
        return None
    artifacts = state.result.get("artifacts") or {}
    key = ARTIFACT_KEYS[artifact_type]
    path_value = artifacts.get(key)
    if not path_value:
        return None
    path = Path(path_value)
    if path.is_absolute():
        return path.resolve()
    return _normalize_artifact_path(tx_root, path_value)


def _artifact_path_from_registry(tx_root: Path, job_id: str, artifact_type: str) -> Optional[Path]:
    registry = _load_registry(tx_root)
    if not registry:
        return None
    key = ARTIFACT_KEYS[artifact_type]
    for entry in registry.values():
        if not isinstance(entry, dict):
            continue
        if entry.get("job_id") and entry["job_id"] != job_id:
            continue
        artifacts = entry.get("artifacts") or {}
        path_value = artifacts.get(key)
        if not path_value:
            continue
        path = _normalize_artifact_path(tx_root, path_value)
        if path:
            return path
    return None


def _resolve_artifact_path(job_id: str, artifact_type: str, state=None, tx_root: Optional[Path] = None) -> Optional[Path]:
    queue = get_queue()
    queue_state = state or queue.get_job(job_id)  # type: ignore[attr-defined]
    if queue_state is not None:
        tx_root = tx_root or (_output_root() / queue_state.request.transaction_id)
        if queue_state.status == JobStatus.SUCCEEDED:
            _update_registry(tx_root, queue_state.request.stage, queue_state)
        path = _artifact_path_from_state(queue_state, tx_root, artifact_type)
        if path:
            return path
        path = _artifact_path_from_registry(tx_root, job_id, artifact_type)
        if path:
            return path
    base = _output_root()
    for registry_path in base.glob("*/registry.json"):
        tx_root = registry_path.parent
        path = _artifact_path_from_registry(tx_root, job_id, artifact_type)
        if path:
            return path
    return None


def _jobs_by_transaction(queue: InProcessJobQueue, transaction_id: str):
    jobs = []
    for state in list(queue._jobs.values()):  # type: ignore[attr-defined]
        if state.request.transaction_id == transaction_id:
            jobs.append(_job_status_body(state))
    return jobs


def _generate_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _resolve_output_root(transaction_id: str, stage: str, job_id: str) -> str:
    base = _output_root()
    return str(base / transaction_id / stage / job_id)


def _require_output_root() -> str:
    base = os.environ.get("PPTX_OUTPUT_ROOT")
    if not base:
        resp = jsonify({"code": "validation_error", "message": "PPTX_OUTPUT_ROOT is required"})
        resp.status_code = 422
        abort(resp)
    return str(Path(base).resolve())


def _output_root() -> Path:
    return Path(_require_output_root())


def _sanitize_for_log(value: str | None) -> str:
    if not value:
        return "-"
    sanitized = re.sub(r"[^\w.-]", "_", str(value))
    if len(sanitized) > 128:
        sanitized = sanitized[:128] + "..."
    return sanitized


def _registry_path(tx_root: Path) -> Path:
    return tx_root / "registry.json"


def _registry_lock_path(tx_root: Path) -> Path:
    return tx_root / ".registry.lock"


def _registry_backup_path(tx_root: Path) -> Path:
    return tx_root / "registry.json.bak"


class RegistryCorruptedError(RuntimeError):
    """既存 registry.json が破損している場合の保護用例外。"""


class RegistryBackupCorruptedError(RuntimeError):
    """バックアップも破損している場合の保護用例外。"""


_registry_thread_locks: dict[str, threading.Lock] = {}
_registry_thread_locks_guard = threading.Lock()


def _get_registry_thread_lock(tx_root: Path) -> threading.Lock:
    key = str(tx_root.resolve())
    with _registry_thread_locks_guard:
        lock = _registry_thread_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _registry_thread_locks[key] = lock
        return lock


def _acquire_file_lock(tx_root: Path):
    lock_path = _registry_lock_path(tx_root)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = lock_path.open("a+")
    if fcntl is not None:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
    elif msvcrt is not None:  # pragma: no cover - Windows
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
    return lock_file


def _release_file_lock(lock_file):
    try:
        if fcntl is not None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        elif msvcrt is not None:  # pragma: no cover - Windows
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        lock_file.close()


@contextmanager
def _lock_registry(tx_root: Path):
    thread_lock = _get_registry_thread_lock(tx_root)
    lock_file = None
    thread_lock.acquire()
    try:
        lock_file = _acquire_file_lock(tx_root)
        yield
    finally:
        if lock_file is not None:
            _release_file_lock(lock_file)
        thread_lock.release()


def _wrap_job(stage: str, job_id: str, transaction_id: str, func):
    logger = logging.getLogger("pptx_generator.api")

    def _runner():
        logger.info("job start stage=%s job_id=%s transaction_id=%s", stage, job_id, transaction_id)
        try:
            result = func()
            logger.info("job succeed stage=%s job_id=%s transaction_id=%s", stage, job_id, transaction_id)
            return result
        except BaseException:  # noqa: BLE001
            logger.exception("job failed stage=%s job_id=%s transaction_id=%s", stage, job_id, transaction_id)
            raise

    return _runner


def _load_registry(tx_root: Path) -> Optional[dict]:
    path = _registry_path(tx_root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger = logging.getLogger("pptx_generator.api")
        logger.warning("registry decode failed path=%s", path)
        backup_path = _registry_backup_path(tx_root)
        if backup_path.exists():
            try:
                return json.loads(backup_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as backup_exc:
                logger.error("registry backup decode failed path=%s", backup_path)
                raise RegistryBackupCorruptedError(str(backup_path)) from backup_exc
        raise RegistryCorruptedError(str(path)) from exc


def _atomic_write_json(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup_path = path.parent / f"{path.name}.bak"
        try:
            backup_path.write_bytes(path.read_bytes())
        except OSError:
            # バックアップが取れなくても本処理は続行する（ログのみ）
            logging.getLogger("pptx_generator.api").warning("registry backup failed path=%s", backup_path)
    fd, tmp_name = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            json.dump(content, tmp_file, ensure_ascii=False, indent=2)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _update_registry(tx_root: Path, stage: str, state) -> None:
    tx_root.mkdir(parents=True, exist_ok=True)
    with _lock_registry(tx_root):
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
        _atomic_write_json(_registry_path(tx_root), registry)


def _resolve_stage_artifacts(tx_root: Path, stage: str, keys: list[str], allow_missing: bool = False) -> dict[str, str]:
    registry = _load_registry(tx_root)
    if registry is None:
        if allow_missing:
            return {}
        resp = jsonify({"code": "not_found", "message": "transaction not found"})
        resp.status_code = 404
        abort(resp)
    entry = registry.get(stage)
    if not entry or "artifacts" not in entry:
        if allow_missing:
            return {}
        resp = jsonify({"code": "validation_error", "message": f"{stage} artifacts not found"})
        resp.status_code = 422
        abort(resp)
    artifacts = entry["artifacts"]
    resolved = {}
    for key in keys:
        path = artifacts.get(key)
        if not path:
            if allow_missing:
                continue
            resp = jsonify({"code": "validation_error", "message": f"{stage} artifacts not found"})
            resp.status_code = 422
            abort(resp)
        resolved[key] = str((tx_root / path).resolve())
    return resolved


def _maybe_update_registry(queue: InProcessJobQueue, job_id: str, tx_root: Path, stage: str) -> None:
    state = queue.get_job(job_id)  # type: ignore[attr-defined]
    if state is None or state.status != JobStatus.SUCCEEDED:
        return
    if stage in ("template", "prepare", "compose", "gen"):
        _update_registry(tx_root, stage, state)


def _latest_job(queue: InProcessJobQueue, transaction_id: str, stage: str):
    latest = None
    for state in list(queue._jobs.values()):  # type: ignore[attr-defined]
        if state.request.transaction_id != transaction_id or state.request.stage != stage:
            continue
        if latest is None:
            latest = state
            continue
        if state.finished_at and latest.finished_at and state.finished_at > latest.finished_at:
            latest = state
    return latest


def _abort_response(status_code: int, code: str, message: str) -> None:
    resp = jsonify({"code": code, "message": message})
    resp.status_code = status_code
    abort(resp)


def _abort_transaction_not_found() -> None:
    _abort_response(404, "not_found", "transaction not found")


def _abort_stage_artifacts_not_found(stage: str) -> None:
    _abort_response(422, "validation_error", f"{stage} artifacts not found")


def _await_latest_state(queue: InProcessJobQueue, state: JobState | None) -> JobState | None:
    if state is None:
        return None
    if state.status not in (JobStatus.SUCCEEDED, JobStatus.FAILED):
        queue.wait(state.request.job_id)
        return queue.get_job(state.request.job_id)  # type: ignore[attr-defined]
    return state


def _refresh_registry_from_state(
    tx_root: Path, stage: str, entry: dict | None, registry: dict | None, state: JobState | None
) -> tuple[dict | None, dict | None]:
    if state is None:
        return entry, registry
    if state.status == JobStatus.SUCCEEDED:
        current_job_id = entry.get("job_id") if isinstance(entry, dict) else None
        if entry is None or current_job_id != state.request.job_id:
            _update_registry(tx_root, stage, state)
            registry = _load_registry(tx_root)
            entry = registry.get(stage) if registry else None
        return entry, registry
    if entry is None and state.status == JobStatus.FAILED:
        _abort_stage_artifacts_not_found(stage)
    return entry, registry


def _handle_missing_entry(allow_missing: bool, registry: dict | None, stage: str) -> dict[str, str]:
    if allow_missing:
        return {}
    if registry is None:
        _abort_transaction_not_found()
    _abort_stage_artifacts_not_found(stage)
    return {}


def _extract_artifacts(entry: dict | None, allow_missing: bool, stage: str) -> dict:
    if not isinstance(entry, dict):
        return _handle_missing_entry(allow_missing, {}, stage)
    artifacts = entry.get("artifacts")
    if artifacts:
        return artifacts
    return _handle_missing_entry(allow_missing, {}, stage)


def _resolve_artifacts_paths(tx_root: Path, artifacts: dict, stage: str, keys: list[str]) -> dict[str, str]:
    resolved = {}
    for key in keys:
        path = artifacts.get(key)
        if not path:
            _abort_stage_artifacts_not_found(stage)
        resolved[key] = str((tx_root / path).resolve())
    return resolved


def _ensure_stage_artifacts(
    queue: InProcessJobQueue, tx_root: Path, transaction_id: str, stage: str, keys: list[str], allow_missing: bool = False
) -> dict[str, str]:
    registry = _load_registry(tx_root)
    entry = registry.get(stage) if registry else None

    state = _await_latest_state(queue, _latest_job(queue, transaction_id, stage))
    entry, registry = _refresh_registry_from_state(tx_root, stage, entry, registry, state)

    if entry is None:
        return _handle_missing_entry(allow_missing, registry, stage)

    artifacts = _extract_artifacts(entry, allow_missing, stage)
    if not artifacts:
        return {}

    return _resolve_artifacts_paths(tx_root, artifacts, stage, keys)
