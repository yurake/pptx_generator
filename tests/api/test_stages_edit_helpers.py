from pathlib import Path
import json

from pptx_generator.pipeline import edit_runner


def test_apply_and_save_edits_writes_json(tmp_path, monkeypatch):
    calls = {}

    def fake_apply(pptx_path, edits, output_path):
        calls["args"] = (pptx_path, tuple(edits), output_path)
        return ["applied"], []

    monkeypatch.setattr(edit_runner, "apply_shape_text_edits", fake_apply)

    output = edit_runner.apply_and_save_edits(
        tmp_path / "input.pptx",
        [{"shape_id": 1, "contents": "hello"}],
        output_path=tmp_path / "out.pptx",
        models={"b", "a"},
    )

    assert output["models"] == ["a", "b"]
    assert output["artifacts"]["pptx_url"].endswith("out.pptx")
    applied_path = Path(output["edits_path"])
    payload = json.loads(applied_path.read_text(encoding="utf-8"))
    assert payload["edits"][0]["shape_id"] == 1
    assert calls["args"][0].name == "input.pptx"
    assert calls["args"][2].name == "out.pptx"


def test_normalize_edits_for_save_filters_invalid():
    edits = [
        {"shape_id": "1", "contents": "<b>ok</b>", "edit": True, "fit": True},
        {"shape_id": "2", "contents": "skip", "edit": False},  # edit=False は除外
        {"shape_id": None, "contents": "ng"},
        {"shape_id": "x", "contents": "ng"},
    ]
    normalized = edit_runner._normalize_edits_for_save(edits)  # type: ignore[attr-defined]
    assert normalized == [
        {"shape_id": 1, "slide_index": None, "name": None, "contents": "ok", "fit": True},
    ]
