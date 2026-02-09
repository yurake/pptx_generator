from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable


def _infer_context_path() -> Path:
    explicit = os.environ.get("PPTX_CONTEXT_PATH")
    if explicit:
        return Path(explicit).expanduser().resolve()

    # 優先: 出力ディレクトリ(PPTX_OUTPUT_DIR / PPTX_PREPARE_OUTPUT_DIR)の親に hook_context.json を置く
    for env_name in ("PPTX_OUTPUT_DIR", "PPTX_PREPARE_OUTPUT_DIR"):
        env_val = os.environ.get(env_name)
        if isinstance(env_val, str) and env_val.strip():
            base = Path(env_val).expanduser().resolve()
            return base.parent / "hook_context.json"

    return Path(".pptx/runtime/hook_context.json").resolve()


CONTEXT_PATH = _infer_context_path()
INPUTS_JSON_PATH = Path(__file__).resolve().parent.parent / "input/inputs.json"
INPUTS_BASE_DIR = INPUTS_JSON_PATH.parent.parent
KEEP_TEMPLATE_SENTINEL = "__KEEP_TEMPLATE__"


def load_context() -> dict[str, Any]:
    if CONTEXT_PATH.exists():
        try:
            return json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def persist_context(context: dict[str, Any]) -> None:
    CONTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTEXT_PATH.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")


def load_inputs_json() -> dict[str, Any]:
    if INPUTS_JSON_PATH.exists():
        try:
            return json.loads(INPUTS_JSON_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def resolve_local_path(path_value: str, anchor: Path | None = None) -> Path:
    base_dir = anchor if anchor is not None else Path(__file__).resolve().parent
    candidate = Path(path_value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (base_dir / candidate).resolve()


def resolve_input_path(
    *,
    env_var: str | None,
    inputs_key: str,
    context: dict[str, Any],
    validator: Callable[[Path], bool] | None = None,
) -> Path:
    """
    共通の入力パス解決ロジック。
    優先順位: 環境変数 -> inputs.json -> context -> エラー
    """
    candidates: list[tuple[str, str]] = []

    if env_var:
        env_value = os.environ.get(env_var)
        if isinstance(env_value, str) and env_value.strip():
            candidates.append((env_value.strip(), "env"))

    inputs = load_inputs_json()
    inputs_value = inputs.get(inputs_key)
    if isinstance(inputs_value, str) and inputs_value.strip():
        candidates.append((inputs_value.strip(), "inputs.json"))

    ctx_value = context.get(inputs_key)
    if isinstance(ctx_value, str) and ctx_value.strip():
        candidates.append((ctx_value.strip(), "context"))

    errors: list[str] = []
    for raw, source in candidates:
        resolved = resolve_local_path(raw, INPUTS_BASE_DIR)
        if resolved.exists() and (validator(resolved) if validator else True):
            context[inputs_key] = str(resolved)
            return resolved
        errors.append(f"{source}: {resolved}")

    msg_lines = [f"{inputs_key} could not be resolved. Provide one of:"]
    if env_var:
        msg_lines.append(f"- env {env_var}")
    msg_lines.append(f"- {INPUTS_JSON_PATH} key '{inputs_key}'")
    msg_lines.append(f"- context field '{inputs_key}' (persisted automatically when resolved)")
    if errors:
        msg_lines.append("Tried paths: " + ", ".join(errors))
    raise FileNotFoundError("\n".join(msg_lines))


def load_mapping_config(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def is_keep_template_value(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip() == KEEP_TEMPLATE_SENTINEL
    if isinstance(value, list):
        return any(is_keep_template_value(item) for item in value)
    if isinstance(value, dict):
        return any(is_keep_template_value(v) for v in value.values())
    return False


# 以下、cost で使用していたユーティリティを共通化
# Excel抽出は cost/stage_shared のロジックを直接利用する想定（共通側では持たない）
