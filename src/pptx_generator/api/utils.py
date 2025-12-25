from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Iterable

from flask import abort, jsonify, request
from werkzeug.utils import secure_filename


def abort_error(status_code: int, code: str, message: str) -> None:
    resp = jsonify({"code": code, "message": message})
    resp.status_code = status_code
    abort(resp)


def require_json() -> dict:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        resp = jsonify({"code": "bad_request", "message": "invalid json payload"})
        resp.status_code = 400
        abort(resp)
    return payload


def require_fields(payload: dict, fields: Iterable[str]) -> None:
    missing = [field for field in fields if payload.get(field) in (None, "")]
    if missing:
        abort_error(422, "validation_error", f"{', '.join(missing)} is required")


def require_path_exists(path: str | Path | None, field: str) -> None:
    if path is None:
        abort_error(422, "validation_error", f"{field} is required")
    p = Path(path)
    if not p.exists():
        abort_error(422, "validation_error", f"{field} not found")


def parse_payload(stage: str) -> dict:
    """JSON を基本とし、templates/prepare は multipart も受け付ける。"""
    if stage in {"template", "prepare"} and request.mimetype and request.mimetype.startswith("multipart/"):
        data: dict = {}
        for key, values in request.form.lists():
            if key == "prepare_sources":
                data[key] = values
            elif len(values) == 1:
                data[key] = values[0]
            else:
                data[key] = values
        return data
    return require_json()


def save_uploaded_files(tx_root: Path, files: Iterable, allowed_ext: set[str]) -> list[Path]:
    uploads_dir = tx_root / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    logger = logging.getLogger("pptx_generator.api")
    for f in files:
        filename = getattr(f, "filename", "") or ""
        if not filename:
            continue
        safe = secure_filename(filename)
        if not safe:
            continue
        ext = Path(safe).suffix.lower()
        if ext and ext not in allowed_ext:
            abort_error(422, "validation_error", "unsupported file extension")
        new_name = f"{Path(safe).stem}_{uuid.uuid4().hex}{ext}"
        dest = uploads_dir / new_name
        f.save(dest)
        try:
            size = dest.stat().st_size
        except OSError:
            size = None
        logger.info("upload saved path=%s size=%s", dest, size)
        saved.append(dest)
    return saved
