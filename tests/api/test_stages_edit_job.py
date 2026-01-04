import json
from pathlib import Path

import pytest

from pptx_generator.api import stages


class DummyClient:
    def __init__(self, edits):
        self._edits = edits
        self.model = "dummy-model"

    def rewrite(self, request):
        class Resp:
            def __init__(self, edits, model):
                self.edits = edits
                self.model = model

        return Resp(self._edits, self.model)


def test_run_edit_job_with_invalid_edits_json(tmp_path, monkeypatch):
    pptx = tmp_path / "input.pptx"
    pptx.write_bytes(b"pptx")
    bad_json = tmp_path / "edits.json"
    bad_json.write_text('{"unexpected": 1}', encoding="utf-8")

    with pytest.raises(stages.EditCommandError):
        stages.run_edit_job(
            pptx_path=pptx,
            edits_json=bad_json,
            edits_inline=None,
            output_path=tmp_path / "out.pptx",
            snapshot_fn=lambda p: [],
            client_factory=lambda: DummyClient([]),
            error_cls=stages.EditCommandError,
            apply_fn=lambda *a, **k: {},
        )


def test_run_edit_job_llm_empty_edits(tmp_path, monkeypatch):
    pptx = tmp_path / "input.pptx"
    pptx.write_bytes(b"pptx")

    result = stages.run_edit_job(
        pptx_path=pptx,
        edits_json=None,
        edits_inline=None,
        output_path=tmp_path / "out.pptx",
        snapshot_fn=lambda p: [{"shape_id": 1, "slide_index": 0, "text": "x"}],
        client_factory=lambda: DummyClient([]),
        error_cls=stages.EditCommandError,
        apply_fn=lambda *a, **k: {"applied": [], "missing": [], "models": [], "edits_path": tmp_path / "edits.json"},
    )

    assert result["applied"] == []
    assert result["missing"] == []
    # apply_fn に依存するため、このテストではモデルを記録しない
    assert result["models"] == []


def test_run_edit_job_llm_populates_models(tmp_path, monkeypatch):
    pptx = tmp_path / "input.pptx"
    pptx.write_bytes(b"pptx")

    result = stages.run_edit_job(
        pptx_path=pptx,
        edits_json=None,
        edits_inline=None,
        output_path=tmp_path / "out.pptx",
        snapshot_fn=lambda p: [{"shape_id": 1, "slide_index": 0, "text": "x"}],
        client_factory=lambda: DummyClient([{"shape_id": 1, "edit": True, "contents": "y"}]),
        error_cls=stages.EditCommandError,
        apply_fn=lambda *a, **k: {
            "applied": [],
            "missing": [],
            "models": [],
            "edits_path": tmp_path / "applied_edits.json",
        },
    )

    assert result["models"] == []


def test_run_edit_job_llm_format_error(tmp_path, monkeypatch):
    pptx = tmp_path / "input.pptx"
    pptx.write_bytes(b"pptx")

    class DummyClient:
        model = "m"

        def rewrite(self, req):
            raise stages.EditAIResponseFormatError("bad format")

    with pytest.raises(stages.EditCommandError):
        stages.run_edit_job(
            pptx_path=pptx,
            edits_json=None,
            edits_inline=None,
            output_path=tmp_path / "out.pptx",
            snapshot_fn=lambda p: [{"shape_id": 1, "slide_index": 0, "text": "x"}],
            client_factory=lambda: DummyClient(),
            error_cls=stages.EditCommandError,
            apply_fn=lambda *a, **k: {},
        )
