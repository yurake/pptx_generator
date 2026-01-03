from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Callable

from pptx_generator.pipeline.text_edit import apply_shape_text_edits, snapshot_shapes_for_edit
from pptx_generator.edit_ai import create_edit_ai_client, EditAIRequest, build_user_prompt
from pptx_generator.edit_ai.client import EditAIResponseFormatError


class EditRunError(RuntimeError):
    """edit 実行時の共通エラー。"""


def load_edits(edits_path: Path, *, error_cls: type[Exception] = EditRunError) -> list[dict]:
    payload = json.loads(edits_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "edits" in payload:
        return payload.get("edits", [])
    if isinstance(payload, list):
        return payload
    raise error_cls('edits ファイルの形式が不正です。リストまたは {"edits": [...]} を指定してください。')


def resolve_explicit_edits(
    edits_json: str | Path | None,
    edits_inline: object,
    *,
    error_cls: type[Exception] = EditRunError,
) -> list[dict] | None:
    if edits_json:
        json_path = Path(edits_json).expanduser()
        if not json_path.exists():
            raise error_cls(f"edits_json not found: {json_path}")
        edits = load_edits(json_path, error_cls=error_cls)
        if not isinstance(edits, list):
            raise error_cls("edits はリストである必要があります")
        return edits
    if edits_inline is not None:
        if not isinstance(edits_inline, list):
            raise error_cls("edits must be a list when provided inline")
        return edits_inline
    return None


def generate_edits_via_llm(
    pptx_path: Path,
    *,
    snapshot_fn: Callable[[Path], list[dict]] = snapshot_shapes_for_edit,
    client_factory: Callable[[], object] = create_edit_ai_client,
) -> tuple[list[dict], set[str]]:
    shapes = snapshot_fn(pptx_path)
    client = client_factory()
    all_edits: list[dict[str, object]] = []
    models: set[str] = set()

    slides: dict[int, list[dict[str, object]]] = {}
    for shape in shapes:
        slides.setdefault(int(shape.get("slide_index", 0)), []).append(shape)

    for slide_idx, contexts in slides.items():
        prompt = build_user_prompt(slide_title=None, shape_contexts=contexts)
        request = EditAIRequest(prompt=prompt, shape_contexts=contexts)
        response = client.rewrite(request)
        models.add(response.model)
        for edit in response.edits:
            if isinstance(edit, dict):
                edit["slide_index"] = slide_idx
            all_edits.append(edit)

    return all_edits, models


def apply_and_save_edits(
    pptx_path: Path, edits: list[dict], *, output_path: Path, models: Iterable[str] | set[str] | list[str]
):
    applied, missing = apply_shape_text_edits(pptx_path, edits, output_path=output_path)
    normalized_edits = _normalize_edits_for_save(edits)
    edits_path = _save_applied_edits(output_path, normalized_edits)
    return {
        "artifacts": {"pptx_url": str(output_path)},
        "applied": applied,
        "missing": missing,
        "models": sorted(models),
        "edits_path": str(edits_path),
    }


def run_edit_job(
    *,
    pptx_path: Path,
    edits_json: str | Path | None,
    edits_inline: object,
    output_path: Path,
    snapshot_fn: Callable[[Path], list[dict]] = snapshot_shapes_for_edit,
    client_factory: Callable[[], object] = create_edit_ai_client,
    error_cls: type[Exception] = EditRunError,
    apply_fn: Callable[[Path, list[dict]], dict] | None = None,
):
    """差分適用の共通実行フロー（CLI/API両用）。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    explicit = resolve_explicit_edits(edits_json, edits_inline, error_cls=error_cls)
    if explicit is not None:
        return (apply_fn or apply_and_save_edits)(pptx_path, explicit, output_path=output_path, models=[])
    try:
        llm_edits, models = generate_edits_via_llm(
            pptx_path,
            snapshot_fn=snapshot_fn,
            client_factory=client_factory,
        )
    except EditAIResponseFormatError as exc:
        raise error_cls(str(exc)) from exc
    return (apply_fn or apply_and_save_edits)(pptx_path, llm_edits, output_path=output_path, models=models)


def _save_applied_edits(output_path: Path, applied: list[dict]) -> Path:
    edits_path = output_path.parent / "applied_edits.json"
    edits_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"edits": applied}
    edits_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return edits_path


def _normalize_edits_for_save(edits: list[dict] | tuple | set) -> list[dict]:
    normalized: list[dict] = []
    for edit in edits:
        if not isinstance(edit, dict):
            continue
        if not edit.get("edit", True):
            continue
        shape_id = edit.get("shape_id")
        contents = edit.get("contents")
        if shape_id is None or contents is None:
            continue
        try:
            shape_id_int = int(shape_id)
        except (TypeError, ValueError):
            continue
        try:
            slide_idx = int(edit.get("slide_index")) if edit.get("slide_index") is not None else None
        except (TypeError, ValueError):
            slide_idx = None
        name_val = edit.get("name")
        normalized.append(
            {
                "shape_id": shape_id_int,
                "slide_index": slide_idx,
                "name": str(name_val) if name_val is not None else None,
                "contents": str(contents),
            }
        )
    return normalized


__all__ = [
    "EditRunError",
    "load_edits",
    "resolve_explicit_edits",
    "generate_edits_via_llm",
    "apply_and_save_edits",
]
