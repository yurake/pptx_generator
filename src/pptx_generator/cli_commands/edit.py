from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import click

from pptx_generator.pipeline.text_edit import apply_shape_text_edits, snapshot_shapes_for_edit
from pptx_generator.edit_ai import create_edit_ai_client, EditAIRequest, build_user_prompt
from pptx_generator.runtime.job_queue import run_job_sync
from pptx_generator.runtime.paths import ensure_stage_output_dir


def _load_edits(edits_path: Path) -> Iterable[dict]:
    payload = json.loads(edits_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "edits" in payload:
        return payload.get("edits", [])
    if isinstance(payload, list):
        return payload
    raise ValueError("edits ファイルの形式が不正です。リストまたは {\"edits\": [...]} を指定してください。")


def create_edit_command(default_output_dir: Path | None = None):
    @click.command("edit", help="PPTX を入力し、shape_id ベースでテキスト差し替えを適用する。edits JSON 未指定時は LLM で自動適用。")
    @click.argument("pptx_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--edits-json", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="差分JSON（shape_id, edit, contents を含むリスト）。指定時は LLM を呼び出さず適用のみ実施")
    @click.option("--output", "output_path", type=click.Path(dir_okay=False, path_type=Path), help="出力先 PPTX パス（省略時は既定の stage 出力ディレクトリ配下）")
    def command(pptx_path: Path, edits_json: Path | None, output_path: Path | None) -> None:
        def _run_edit() -> dict[str, object]:
            resolved_dir = ensure_stage_output_dir("edit")
            resolved_output = output_path or (resolved_dir / pptx_path.name)
            resolved_output.parent.mkdir(parents=True, exist_ok=True)

            if edits_json is not None:
                edits = _load_edits(edits_json)
                applied, missing = apply_shape_text_edits(pptx_path, edits, output_path=resolved_output)
                return {
                    "applied": applied,
                    "missing": missing,
                    "models": [],
                    "output": resolved_output,
                }

            shapes = snapshot_shapes_for_edit(pptx_path)
            client = create_edit_ai_client()
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

            applied, missing = apply_shape_text_edits(pptx_path, all_edits, output_path=resolved_output)
            return {
                "applied": applied,
                "missing": missing,
                "models": sorted(models),
                "output": resolved_output,
            }

        result = run_job_sync(stage="edit", func=_run_edit)
        click.echo(f"適用件数: {result['applied']}, 未適用 shape_id: {result['missing']}")
        if result.get("models"):
            click.echo(f"モデル: {', '.join(result['models'])}")
        click.echo(f"出力: {result['output']}")

    return command


__all__ = ["create_edit_command"]
