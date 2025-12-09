from __future__ import annotations

from pathlib import Path

import pytest

from pptx_generator.cli_handlers.outline import run_draft_pipeline
from pptx_generator.models import JobAuth, JobMeta, JobSpec
from pptx_generator.pipeline import DraftStructuringOptions


def test_run_draft_pipeline_assigns_store_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    spec = JobSpec(
        meta=JobMeta(schema_version="1.0", title="Outline Deck"),
        auth=JobAuth(created_by="tester"),
        slides=[],
    )
    draft_options = DraftStructuringOptions(output_dir=None, draft_store_dir=None)

    class DummyNormalizeStep:
        def __init__(self, options) -> None:  # noqa: ANN001
            self.options = options

    class DummyDraftStep:
        def __init__(self, options) -> None:  # noqa: ANN001
            self.options = options

    captured_context: dict[str, object] = {}

    class DummyRunner:
        def __init__(self, steps) -> None:  # noqa: ANN001
            self.steps = steps

        def execute(self, context) -> None:  # noqa: ANN001
            captured_context["context"] = context

    monkeypatch.setattr("pptx_generator.cli_handlers.outline.PrepareNormalizationStep", DummyNormalizeStep)
    monkeypatch.setattr("pptx_generator.cli_handlers.outline.DraftStructuringStep", DummyDraftStep)
    monkeypatch.setattr("pptx_generator.cli_handlers.outline.PipelineRunner", DummyRunner)

    context = run_draft_pipeline(
        spec=spec,
        output_dir=tmp_path,
        prepare_cards=None,
        require_prepare=False,
        draft_options=draft_options,
    )

    assert captured_context["context"] is context
    expected_store_dir = tmp_path / "store"
    assert draft_options.draft_store_dir == expected_store_dir
