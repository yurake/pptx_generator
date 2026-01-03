from __future__ import annotations

from pathlib import Path
from typing import Iterable

import click

from pptx_generator.pipeline.text_edit import apply_shape_text_edits, snapshot_shapes_for_edit
from pptx_generator.edit_ai import create_edit_ai_client, EditAIRequest, build_user_prompt
from pptx_generator.runtime.job_queue import run_job_sync
from pptx_generator.settings.paths import build_output_dir
from pptx_generator.pipeline.edit_runner import (
    resolve_explicit_edits,
    generate_edits_via_llm,
    apply_and_save_edits,
    EditRunError,
)


def _resolve_output_path(default_output_dir: Path | None, output_path: Path | None, pptx_path: Path) -> Path:
    base_output_dir = default_output_dir or build_output_dir("edit")
    resolved_output = output_path or (base_output_dir / pptx_path.name)
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    return resolved_output


def _apply_edits(pptx_path: Path, edits: list[dict], resolved_output: Path) -> dict[str, object]:
    result = apply_and_save_edits(pptx_path, edits, output_path=resolved_output, models=[])
    return {
        "applied": result["applied"],
        "missing": result["missing"],
        "models": result.get("models", []),
        "output": resolved_output,
    }


def create_edit_command(default_output_dir: Path | None = None):
    @click.command("edit", help="PPTX を入力し、shape_id ベースでテキスト差し替えを適用する。edits JSON 未指定時は LLM で自動適用。")
    @click.argument("pptx_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option("--edits-json", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="差分JSON（shape_id, edit, contents を含むリスト）。指定時は LLM を呼び出さず適用のみ実施")
    @click.option("--output", "output_path", type=click.Path(dir_okay=False, path_type=Path), help="出力先 PPTX パス（省略時は既定の stage 出力ディレクトリ配下）")
    def command(pptx_path: Path, edits_json: Path | None, output_path: Path | None) -> None:
        def _run_edit() -> dict[str, object]:
            resolved_output = _resolve_output_path(default_output_dir, output_path, pptx_path)

            explicit_edits = resolve_explicit_edits(edits_json, None, error_cls=ValueError)
            if explicit_edits is not None:
                return _apply_edits(pptx_path, explicit_edits, resolved_output)

            all_edits, models = generate_edits_via_llm(
                pptx_path,
                snapshot_fn=snapshot_shapes_for_edit,
                client_factory=create_edit_ai_client,
            )
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
