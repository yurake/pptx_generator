from __future__ import annotations

from pathlib import Path

from flask import request

from pptx_generator.api.utils import abort_error, require_fields, require_path_exists, save_uploaded_files
from pptx_generator.runtime.job_queue import InProcessJobQueue

ALLOWED_UPLOAD_EXT = {".pptx", ".md", ".txt", ".json"}


def prepare_template_payload(tx_root: Path, payload: dict) -> dict:
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


def prepare_prepare_payload(queue: InProcessJobQueue, tx_root: Path, transaction_id: str, payload: dict) -> dict:
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
    payload["mode"] = (payload.get("mode") or "static").lower()
    if payload["mode"] != "static":
        abort_error(422, "validation_error", "mode must be static")
    return payload
