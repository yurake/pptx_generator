from pathlib import Path

import pytest

from pptx_generator.api import stages


def test_build_edit_job_missing_pptx(tmp_path):
    with pytest.raises(stages.EditCommandError):
        stages.build_edit_job({"pptx_path": tmp_path / "missing.pptx"}, tmp_path)


def test_load_edits_invalid(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('"string"', encoding="utf-8")
    with pytest.raises(stages.EditCommandError):
        stages._load_edits(bad)  # noqa: SLF001


def test_resolve_explicit_edits_inline_type_error():
    with pytest.raises(stages.EditCommandError):
        stages._resolve_explicit_edits({"edits_inline": "not-a-list"})  # noqa: SLF001


def test_apply_and_save_edits_writes_file(tmp_path, monkeypatch):
    pptx = tmp_path / "in.pptx"
    pptx.write_bytes(b"pptx")

    monkeypatch.setattr(stages, "apply_shape_text_edits", lambda *a, **k: ([{"shape_id": 1}], []))
    result = stages._apply_and_save_edits(  # noqa: SLF001
        pptx, [{"shape_id": 1, "contents": "x"}], output_path=tmp_path / "out.pptx", models={"b", "a"}
    )

    assert Path(result["edits_path"]).exists()
    assert result["models"] == ["a", "b"]


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

    # stages._generate_edits_via_llm は引数を受け取らないため、edit_runner 経由で検証
    edits, models = stages.generate_edits_via_llm(  # type: ignore[attr-defined]
        tmp_path / "in.pptx", snapshot_fn=snapshot_fn, client_factory=lambda: DummyClient()
    )

    assert called["snapshot"] is True
    assert called["prompt"]
    assert edits[0]["slide_index"] == 0
    assert list(models) == ["m"]
