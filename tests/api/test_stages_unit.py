from pathlib import Path

import pytest

from pptx_generator.api import stages
from pptx_generator.pipeline import edit_runner


def test_build_edit_job_missing_pptx(tmp_path):
    with pytest.raises(stages.EditCommandError):
        stages.build_edit_job({"pptx_path": tmp_path / "missing.pptx"}, tmp_path)


def test_load_edits_invalid(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('"string"', encoding="utf-8")
    with pytest.raises(edit_runner.EditRunError):
        edit_runner.load_edits(bad)


def test_resolve_explicit_edits_inline_type_error():
    with pytest.raises(edit_runner.EditRunError):
        edit_runner.resolve_explicit_edits(None, "not-a-list")


def test_generate_edits_via_llm(tmp_path):
    called = {}

    def snapshot_fn(_):
        called["snapshot"] = True
        return [{"shape_id": 1, "slide_index": 0, "text": "x"}]

    class DummyClient:
        model = "m"

        def rewrite(self, req):
            called["prompt"] = req.prompt
            return type("Resp", (), {"edits": [{"shape_id": 1, "contents": "y"}], "model": "m"})

    edits, models = edit_runner.generate_edits_via_llm(
        tmp_path / "in.pptx", snapshot_fn=snapshot_fn, client_factory=lambda: DummyClient()
    )

    assert called["snapshot"] is True
    assert called["prompt"]
    assert edits[0]["slide_index"] == 0
    assert list(models) == ["m"]
