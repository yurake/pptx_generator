from __future__ import annotations

import logging
import os
import re
import uuid
from pathlib import Path
from typing import Callable

from flask import abort, jsonify

from pptx_generator.api.registry import ensure_stage_artifacts, update_registry
from pptx_generator.api.stages import (
    build_template_job,
    build_prepare_job,
    build_compose_job,
    build_gen_job,
)
from pptx_generator.runtime.job_queue import JobRequest, JobStatus, InProcessJobQueue


PayloadBuilder = Callable[..., dict]


def generate_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def enqueue_job(
    queue: InProcessJobQueue,
    *,
    stage: str,
    job_id: str,
    transaction_id: str,
    payload: dict,
    template_payload_builder: PayloadBuilder,
    prepare_payload_builder: PayloadBuilder,
):
    output_root = require_output_root()
    tx_root = Path(output_root) / transaction_id
    tx_root.mkdir(parents=True, exist_ok=True)
    if stage == "template":
        func = build_template_job(
            payload=template_payload_builder(tx_root, payload),
            workdir=Path(resolve_output_root(transaction_id, stage, job_id)),
        )
    elif stage == "prepare":
        func = build_prepare_job(
            payload=prepare_payload_builder(queue, tx_root, transaction_id, payload),
            workdir=Path(resolve_output_root(transaction_id, stage, job_id)),
            jobspec_path=Path(
                ensure_stage_artifacts(queue, tx_root, transaction_id, "template", ["jobspec_url"])["jobspec_url"]
            ),
            tx_root=tx_root,
        )
    elif stage == "compose":
        func = build_compose_job(
            payload=payload,
            workdir=Path(resolve_output_root(transaction_id, stage, job_id)),
            template_artifacts=ensure_stage_artifacts(queue, tx_root, transaction_id, "template", ["jobspec_url", "diagnostics_url"]),
            prepare_artifacts=ensure_stage_artifacts(queue, tx_root, transaction_id, "prepare", ["prepare_card_url"]),
        )
    elif stage == "gen":
        func = build_gen_job(
            payload=payload,
            workdir=Path(resolve_output_root(transaction_id, stage, job_id)),
            compose_artifacts=ensure_stage_artifacts(queue, tx_root, transaction_id, "compose", ["generate_ready_url"]),
            template_artifacts=ensure_stage_artifacts(queue, tx_root, transaction_id, "template", ["jobspec_url"], allow_missing=True),
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
        func=wrap_job(stage, job_id, transaction_id, func),
    )
    logging.getLogger("pptx_generator.api").info(
        "job enqueued stage=%s job_id=%s transaction_id=%s",
        sanitize_for_log(stage),
        sanitize_for_log(job_id),
        sanitize_for_log(transaction_id),
    )
    state = queue.enqueue(job_request)
    queue.ensure_workers(1)
    return state


def job_response(state):
    body = job_status_body(state)
    return jsonify(body), 202


def job_status_body(state):
    tx_root = output_root() / state.request.transaction_id
    if state.status == JobStatus.SUCCEEDED:
        update_registry(tx_root, state.request.stage, state)
    artifacts = {}
    if state.request.stage == "gen":
        from pptx_generator.api.registry import ARTIFACT_KEYS, resolve_artifact_path, artifact_api_path

        for artifact_type in ARTIFACT_KEYS:
            path = resolve_artifact_path(state.request.job_id, artifact_type, state=state, tx_root=tx_root)
            if path:
                artifacts[ARTIFACT_KEYS[artifact_type]] = artifact_api_path(state.request.job_id, artifact_type)
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
        "error": error_info(state),
    }


def jobs_by_transaction(queue: InProcessJobQueue, transaction_id: str):
    jobs = []
    for state in list(queue._jobs.values()):  # type: ignore[attr-defined]
        if state.request.transaction_id == transaction_id:
            jobs.append(job_status_body(state))
    return jobs


def error_info(state):
    if state.status != JobStatus.FAILED or state.error is None:
        return None
    return {"code": "job_failed", "message": str(state.error)}


def resolve_output_root(transaction_id: str, stage: str, job_id: str) -> str:
    base = output_root()
    return str(base / transaction_id / stage / job_id)


def require_output_root() -> str:
    base = os.environ.get("PPTX_OUTPUT_ROOT")
    if not base:
        resp = jsonify({"code": "validation_error", "message": "PPTX_OUTPUT_ROOT is required"})
        resp.status_code = 422
        abort(resp)
    return str(Path(base).resolve())


def output_root() -> Path:
    return Path(require_output_root())


def sanitize_for_log(value: str | None) -> str:
    if not value:
        return "-"
    sanitized = re.sub(r"[^\w.-]", "_", str(value))
    if len(sanitized) > 128:
        sanitized = sanitized[:128] + "..."
    return sanitized


def wrap_job(stage: str, job_id: str, transaction_id: str, func):
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
