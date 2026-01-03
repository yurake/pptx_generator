from pathlib import Path
import pytest

from pptx_generator.pipeline import edit_runner


def test_resolve_explicit_edits_path_missing(tmp_path):
    with pytest.raises(edit_runner.EditRunError):
        edit_runner.resolve_explicit_edits(tmp_path / "missing.json", None)


def test_apply_and_save_edits_error(tmp_path, monkeypatch):
    pptx = tmp_path / "in.pptx"
    pptx.write_bytes(b"pptx")

    def _fail(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(edit_runner, "_save_applied_edits", _fail)
    monkeypatch.setattr(edit_runner, "apply_shape_text_edits", lambda *a, **k: ([], []))
    with pytest.raises(OSError):
        edit_runner.apply_and_save_edits(pptx, [], output_path=tmp_path / "out.pptx", models=[])
