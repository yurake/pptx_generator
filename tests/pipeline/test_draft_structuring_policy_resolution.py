from __future__ import annotations

from pathlib import Path

from pptx_generator.pipeline.draft_structuring import dynamic_runtime as dyn
from pptx_generator.pipeline.draft_structuring import types as draft_types
from pptx_generator.pipeline.draft_structuring.dynamic_runtime import LayoutProfile
from pptx_generator.settings.ai_policy import PolicyResolution


def test_draft_structuring_options_default_policy(monkeypatch):
    dummy_path = Path("/tmp/layout.json")

    monkeypatch.setattr(
        draft_types,
        "resolve_layout_ai_policy_path",
        lambda: PolicyResolution(dummy_path, "default"),
    )

    options = draft_types.DraftStructuringOptions()
    assert options.layout_ai_policy_path == dummy_path


def test_prepare_dynamic_inputs_logs_when_policy_missing(monkeypatch, caplog):
    monkeypatch.setattr(dyn, "load_layouts", lambda path=None, spec_source_path=None: [
        LayoutProfile(
            layout_id="L1",
            layout_name="Layout One",
            usage_tags=("content",),
            text_hint={},
            media_hint={},
        )
    ])
    monkeypatch.setattr(dyn, "load_analysis_summary", lambda *_: {})
    monkeypatch.setattr(
        dyn,
        "resolve_layout_ai_policy_path",
        lambda path=None: PolicyResolution(None, "missing"),
    )

    class _Step:
        def __init__(self) -> None:
            self.options = draft_types.DraftStructuringOptions(
                layout_ai_policy_path=None,
                layouts_path=None,
                analysis_summary_path=None,
            )

    caplog.set_level("INFO")
    prepare_meta = type("Meta", (), {"mode": "dynamic"})()
    layouts, analyzer_map, recommender, dynamic_prepare = dyn.prepare_dynamic_inputs(
        _Step(),
        context=object(),
        prepare_meta=prepare_meta,
    )

    assert layouts and layouts[0].layout_id == "L1"
    assert analyzer_map == {}
    assert dynamic_prepare is True
    assert recommender is not None
    assert any("simulate フロー" in record.getMessage() for record in caplog.records)
