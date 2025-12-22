import json
from pathlib import Path

from pptx_generator.config_manager import ResolvedConfig
from pptx_generator.models import JobAuth, JobMeta, JobSpec, Slide
from pptx_generator.pipeline import PipelineContext, PipelineStage, StageResult
from pptx_generator.pipeline.trace import write_pipeline_trace


def _build_spec() -> JobSpec:
    return JobSpec(
        meta=JobMeta(schema_version="1.0", title="trace-test"),
        auth=JobAuth(created_by="tester"),
        slides=[Slide(id="s1", layout="title")],
    )


def test_write_pipeline_trace_outputs_json(tmp_path: Path) -> None:
    context = PipelineContext(spec=_build_spec(), workdir=tmp_path)
    context.advance_stage(PipelineStage.PREPARE)
    context.record_stage_result(StageResult(stage=PipelineStage.PREPARE, success=True, details={"ok": True}))
    context.record_error("failure")
    context.config_snapshot = ResolvedConfig(
        values={"template_path": "template.pptx"},
        sources={"template_path": "cli_options"},
        priority_order=("cli_options",),
    )

    path = write_pipeline_trace(context, tmp_path, filename="trace.json")
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path.exists()
    assert payload["job_id"] == context.job_id
    assert payload["transaction_id"] == context.transaction_id
    assert payload["current_stage"] == "prepare"
    assert payload["stage_results"][0]["stage"] == "prepare"
    assert payload["error_history"] == ["failure"]
    assert payload["config_snapshot"]["values"]["template_path"] == "template.pptx"
    assert context.artifacts.get("pipeline_trace_path") == str(path)
