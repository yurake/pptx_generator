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
            apply_fn=stages._apply_and_save_edits,  # noqa: SLF001
        )


def test_run_edit_job_llm_empty_edits(tmp_path, monkeypatch):
    pptx = tmp_path / "input.pptx"
    pptx.write_bytes(b"pptx")

    monkeypatch.setattr(stages, "apply_shape_text_edits", lambda *a, **k: ([], []))

    result = stages.run_edit_job(
        pptx_path=pptx,
        edits_json=None,
        edits_inline=None,
        output_path=tmp_path / "out.pptx",
        snapshot_fn=lambda p: [{"shape_id": 1, "slide_index": 0, "text": "x"}],
        client_factory=lambda: DummyClient([]),
        error_cls=stages.EditCommandError,
        apply_fn=stages._apply_and_save_edits,  # noqa: SLF001
    )

    assert result["applied"] == []
    assert result["missing"] == []
    # edits が空でもモデルは記録される
    assert result["models"] == ["dummy-model"]


def test_run_edit_job_llm_populates_models(tmp_path, monkeypatch):
    pptx = tmp_path / "input.pptx"
    pptx.write_bytes(b"pptx")

    monkeypatch.setattr(stages, "apply_shape_text_edits", lambda *a, **k: ([], []))

    result = stages.run_edit_job(
        pptx_path=pptx,
        edits_json=None,
        edits_inline=None,
        output_path=tmp_path / "out.pptx",
        snapshot_fn=lambda p: [{"shape_id": 1, "slide_index": 0, "text": "x"}],
        client_factory=lambda: DummyClient([{"shape_id": 1, "edit": True, "contents": "y"}]),
        error_cls=stages.EditCommandError,
        apply_fn=stages._apply_and_save_edits,  # noqa: SLF001
    )

    assert result["models"] == ["dummy-model"]
    # applied_edits.json が生成されることを確認
    edits_path = Path(result["edits_path"])
    payload = json.loads(edits_path.read_text(encoding="utf-8"))
    assert payload["edits"][0]["contents"] == "y"


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
            apply_fn=stages._apply_and_save_edits,  # noqa: SLF001
        )
