from pathlib import Path

import pytest

from pptx_generator.models import JobAuth, JobMeta, JobSpec, Slide
from pptx_generator.pipeline import (
    PipelineContext,
    PipelineRunner,
    PipelineStage,
    StageContract,
    StageResult,
)


def _build_spec() -> JobSpec:
    meta = JobMeta(schema_version="1.0", title="test")
    auth = JobAuth(created_by="tester")
    return JobSpec(meta=meta, auth=auth, slides=[Slide(id="s1", layout="title")])


class _DummyStage(StageContract):
    name = "dummy"
    stage = PipelineStage.MAPPING

    def __init__(self) -> None:
        self.validated = False

    def validate_input(self, context: PipelineContext) -> None:  # noqa: D401
        self.validated = True
        assert context.spec.slides

    def execute(self, context: PipelineContext) -> StageResult:
        context.add_artifact("seen", True)
        return StageResult(stage=self.stage, success=True, details={"ok": True})


class _FailingStep:
    name = "fail"

    def run(self, context: PipelineContext) -> None:
        context.add_artifact("before_fail", True)
        raise RuntimeError("boom")


def test_pipeline_context_tracks_stage_and_result(tmp_path: Path) -> None:
    context = PipelineContext(spec=_build_spec(), workdir=tmp_path)
    runner = PipelineRunner([_DummyStage()])

    runner.execute(context)

    assert context.current_stage == PipelineStage.MAPPING
    assert "dummy" in context.execution_trace
    assert PipelineStage.MAPPING.value in context.execution_trace
    assert context.stage_results and context.stage_results[0].details["ok"] is True
    assert context.artifacts["seen"] is True


def test_pipeline_runner_records_errors(tmp_path: Path) -> None:
    context = PipelineContext(spec=_build_spec(), workdir=tmp_path)
    runner = PipelineRunner([_FailingStep()])

    with pytest.raises(RuntimeError):
        runner.execute(context)

    assert "fail" in context.execution_trace
    assert context.error_history[-1] == "boom"
