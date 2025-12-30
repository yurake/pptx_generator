from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import click

from pptx_generator.pipeline.text_edit import apply_shape_text_edits, generate_edits_template


def _load_edits(edits_path: Path) -> Iterable[dict]:
    payload = json.loads(edits_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "edits" in payload:
        return payload.get("edits", [])
    if isinstance(payload, list):
        return payload
    raise ValueError("edits ファイルの形式が不正です。リストまたは {\"edits\": [...]} を指定してください。")


def create_edit_command(default_output_dir: Path | None = None):
    @click.command("edit", help="PPTX を入力し、shape_id ベースでテキスト差し替えを適用する。edits JSON が無い場合はテンプレートを生成。")
    @click.option("--pptx-path", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True, help="対象の PPTX パス")
    @click.option("--edits-json", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="差分JSON（shape_id, edit, contents を含むリスト）")
    @click.option("--output", "output_path", type=click.Path(dir_okay=False, path_type=Path), help="出力先 PPTX パス（省略時は <元ファイル名>_edited.pptx）")
    @click.option("--export-edits", type=click.Path(dir_okay=False, path_type=Path), help="edits テンプレートを書き出すパス（省略時は <元名>_edits.json）")
    def command(pptx_path: Path, edits_json: Path | None, output_path: Path | None, export_edits: Path | None) -> None:
        if edits_json is None:
            target = export_edits or pptx_path.with_name(f\"{pptx_path.stem}_edits.json\")
            output_edits = generate_edits_template(pptx_path, target)
            click.echo(f\"edits テンプレートを出力しました: {output_edits}\")
            click.echo(\"必要に応じて edit=true/contents を更新し、--edits-json で再実行してください。\") 
            return

        edits = _load_edits(edits_json)
        resolved_output = output_path or pptx_path.with_name(f\"{pptx_path.stem}_edited{pptx_path.suffix}\")
        applied, missing = apply_shape_text_edits(pptx_path, edits, output_path=resolved_output)
        click.echo(f\"適用件数: {applied}, 未適用 shape_id: {missing}\")
        click.echo(f\"出力: {resolved_output}\")

    return command


__all__ = ["create_edit_command"]
