from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from flask import abort, jsonify

from pptx_generator.runtime.job_queue import JobStatus, InProcessJobQueue, JobState, get_queue

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None

try:
    import msvcrt
except ImportError:  # pragma: no cover - non-Windows
    msvcrt = None

ARTIFACT_KEYS = {"pptx": "pptx_url", "pdf": "pdf_url"}


class RegistryCorruptedError(RuntimeError):
    """既存 registry.json が破損している場合の保護用例外。"""


class RegistryBackupCorruptedError(RuntimeError):
    """バックアップも破損している場合の保護用例外。"""


_registry_thread_locks: dict[str, threading.Lock] = {}
_registry_thread_locks_guard = threading.Lock()


def artifact_api_path(job_id: str, artifact_type: str) -> str:
    return f"/jobs/{job_id}/artifacts/{artifact_type}"


def resolve_artifact_path(job_id: str, artifact_type: str, state=None, tx_root: Optional[Path] = None) -> Optional[Path]:
    queue = get_queue()
    queue_state = state or queue.get_job(job_id)  # type: ignore[attr-defined]
    if queue_state is not None:
        tx_root = tx_root or (output_root() / queue_state.request.transaction_id)
        if queue_state.status == JobStatus.SUCCEEDED:
            update_registry(tx_root, queue_state.request.stage, queue_state)
        path = artifact_path_from_state(queue_state, tx_root, artifact_type)
        if path:
            return path
        path = artifact_path_from_registry(tx_root, job_id, artifact_type)
        if path:
            return path
    base = output_root()
    for registry_path in base.glob("*/registry.json"):
        tx_root = registry_path.parent
        path = artifact_path_from_registry(tx_root, job_id, artifact_type)
        if path:
            return path
    return None


def update_registry(tx_root: Path, stage: str, state) -> None:
    tx_root.mkdir(parents=True, exist_ok=True)
    with lock_registry(tx_root):
        registry = load_registry(tx_root) or {}
        artifacts = {}
        if isinstance(state.result, dict):
            artifacts = state.result.get("artifacts") or {}
        rel_artifacts = {}
        for key, value in artifacts.items():
            p = Path(value)
            try:
                rel = p.relative_to(tx_root)
                rel_artifacts[key] = str(rel)
            except ValueError:
                rel_artifacts[key] = value
        registry[stage] = {"job_id": state.request.job_id, "artifacts": rel_artifacts}
        atomic_write_json(registry_path(tx_root), registry)


def ensure_stage_artifacts(
    queue: InProcessJobQueue, tx_root: Path, transaction_id: str, stage: str, keys: list[str], allow_missing: bool = False
) -> dict[str, str]:
    registry = load_registry(tx_root)
    entry = registry.get(stage) if registry else None

    state = await_latest_state(queue, latest_job(queue, transaction_id, stage))
    entry, registry = refresh_registry_from_state(tx_root, stage, entry, registry, state)

    if entry is None:
        return handle_missing_entry(allow_missing, registry, stage)

    artifacts = extract_artifacts(entry, allow_missing, stage)
    if not artifacts:
        return {}

    return resolve_artifacts_paths(tx_root, artifacts, stage, keys)


def await_latest_state(queue: InProcessJobQueue, state: JobState | None) -> JobState | None:
    if state is None:
        return None
    if state.status not in (JobStatus.SUCCEEDED, JobStatus.FAILED):
        queue.wait(state.request.job_id)
        return queue.get_job(state.request.job_id)  # type: ignore[attr-defined]
    return state


def refresh_registry_from_state(
    tx_root: Path, stage: str, entry: dict | None, registry: dict | None, state: JobState | None
) -> tuple[dict | None, dict | None]:
    if state is None:
        return entry, registry
    if state.status == JobStatus.SUCCEEDED:
        current_job_id = entry.get("job_id") if isinstance(entry, dict) else None
        if entry is None or current_job_id != state.request.job_id:
            update_registry(tx_root, stage, state)
            registry = load_registry(tx_root)
            entry = registry.get(stage) if registry else None
        return entry, registry
    if entry is None and state.status == JobStatus.FAILED:
        abort_stage_artifacts_not_found(stage)
    return entry, registry


def handle_missing_entry(allow_missing: bool, registry: dict | None, stage: str) -> dict[str, str]:
    if allow_missing:
        return {}
    if registry is None:
        abort_transaction_not_found()
    abort_stage_artifacts_not_found(stage)
    return {}


def extract_artifacts(entry: dict | None, allow_missing: bool, stage: str) -> dict:
    if not isinstance(entry, dict):
        return handle_missing_entry(allow_missing, {}, stage)
    artifacts = entry.get("artifacts")
    if artifacts:
        return artifacts
    return handle_missing_entry(allow_missing, {}, stage)


def resolve_artifacts_paths(tx_root: Path, artifacts: dict, stage: str, keys: list[str]) -> dict[str, str]:
    resolved = {}
    for key in keys:
        path = artifacts.get(key)
        if not path:
            abort_stage_artifacts_not_found(stage)
        resolved[key] = str((tx_root / path).resolve())
    return resolved


def latest_job(queue: InProcessJobQueue, transaction_id: str, stage: str):
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


def abort_response(status_code: int, code: str, message: str) -> None:
    resp = jsonify({"code": code, "message": message})
    resp.status_code = status_code
    abort(resp)


def abort_transaction_not_found() -> None:
    abort_response(404, "not_found", "transaction not found")


def abort_stage_artifacts_not_found(stage: str) -> None:
    abort_response(422, "validation_error", f"{stage} artifacts not found")


def artifact_path_from_state(state, tx_root: Path, artifact_type: str) -> Optional[Path]:
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
    return normalize_artifact_path(tx_root, path_value)


def artifact_path_from_registry(tx_root: Path, job_id: str, artifact_type: str) -> Optional[Path]:
    registry = load_registry(tx_root)
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
        path = normalize_artifact_path(tx_root, path_value)
        if path:
            return path
    return None


def normalize_artifact_path(tx_root: Path, path_value: str) -> Optional[Path]:
    path = Path(path_value)
    if path.is_absolute():
        return path.resolve()
    resolved = (tx_root / path).resolve()
    try:
        resolved.relative_to(tx_root)
    except ValueError:
        return None
    return resolved


def registry_path(tx_root: Path) -> Path:
    return tx_root / "registry.json"


def registry_lock_path(tx_root: Path) -> Path:
    return tx_root / ".registry.lock"


def registry_backup_path(tx_root: Path) -> Path:
    return tx_root / "registry.json.bak"


def get_registry_thread_lock(tx_root: Path) -> threading.Lock:
    key = str(tx_root.resolve())
    with _registry_thread_locks_guard:
        lock = _registry_thread_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _registry_thread_locks[key] = lock
        return lock


def acquire_file_lock(tx_root: Path):
    lock_path = registry_lock_path(tx_root)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = lock_path.open("a+")
    if fcntl is not None:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
    elif msvcrt is not None:  # pragma: no cover - Windows
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
    return lock_file


def release_file_lock(lock_file):
    try:
        if fcntl is not None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        elif msvcrt is not None:  # pragma: no cover - Windows
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        lock_file.close()


@contextmanager
def lock_registry(tx_root: Path):
    thread_lock = get_registry_thread_lock(tx_root)
    lock_file = None
    thread_lock.acquire()
    try:
        lock_file = acquire_file_lock(tx_root)
        yield
    finally:
        if lock_file is not None:
            release_file_lock(lock_file)
        thread_lock.release()


def load_registry(tx_root: Path) -> Optional[dict]:
    path = registry_path(tx_root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger = logging.getLogger("pptx_generator.api")
        logger.warning("registry decode failed path=%s", path)
        backup_path = registry_backup_path(tx_root)
        if backup_path.exists():
            try:
                return json.loads(backup_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as backup_exc:
                logger.error("registry backup decode failed path=%s", backup_path)
                raise RegistryBackupCorruptedError(str(backup_path)) from backup_exc
        raise RegistryCorruptedError(str(path)) from exc


def atomic_write_json(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup_path = path.parent / f"{path.name}.bak"
        try:
            backup_path.write_bytes(path.read_bytes())
        except OSError:
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


def output_root() -> Path:
    base = os.environ.get("PPTX_OUTPUT_ROOT")
    if not base:
        resp = jsonify({"code": "validation_error", "message": "PPTX_OUTPUT_ROOT is required"})
        resp.status_code = 422
        abort(resp)
    return Path(base).resolve()
