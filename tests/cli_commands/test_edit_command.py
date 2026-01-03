from pathlib import Path

import click.testing

from pptx_generator.cli_commands import edit as edit_cmd


def _dummy_apply(pptx_path, edits, output_path):
    return edits, []


def test_edit_command_explicit_edits(tmp_path, monkeypatch):
    pptx = tmp_path / "in.pptx"
    pptx.write_bytes(b"dummy")
    edits_file = tmp_path / "edits.json"
    edits_file.write_text('[{"shape_id": 1, "contents": "x"}]', encoding="utf-8")

    monkeypatch.setattr(edit_cmd, "apply_shape_text_edits", _dummy_apply)
    monkeypatch.setattr(edit_cmd, "snapshot_shapes_for_edit", lambda pptx: [])
    monkeypatch.setattr(edit_cmd, "create_edit_ai_client", lambda: None)

    runner = click.testing.CliRunner()
    cmd = edit_cmd.create_edit_command(default_output_dir=tmp_path)
    result = runner.invoke(cmd, [str(pptx), "--edits-json", str(edits_file)])

    assert result.exit_code == 0
    assert "適用件数" in result.output
    out_pptx = tmp_path / "in.pptx"
    assert out_pptx.exists()


def test_resolve_output_path_default(tmp_path):
    pptx = tmp_path / "in.pptx"
    pptx.write_bytes(b"x")
    resolved = edit_cmd._resolve_output_path(tmp_path / ".pptx/edit", None, pptx)
    assert resolved.parent.exists()
    assert resolved.name == "in.pptx"
