import logging

from pptx_generator.pipeline import PipelineContext, PipelineRunner, PipelineStage
from pptx_generator.pipeline.base import PipelineStep
from pptx_generator.models import JobSpec, JobMeta, JobAuth


class DummyStep(PipelineStep):
    name = "dummy"
    stage = PipelineStage.PREPARE

    def run(self, context: PipelineContext) -> None:  # pragma: no cover - minimal behavior
        return None


def test_pipeline_runner_logs_truncated_ids(caplog, tmp_path):
    context = PipelineContext(
        spec=JobSpec(meta=JobMeta(schema_version="1.0", title="t"), auth=JobAuth(created_by="cli"), slides=[]),
        workdir=tmp_path,
        job_id="job-1234567890",
        transaction_id="tx-abcdef123456",
    )
    runner = PipelineRunner([DummyStep()])

    with caplog.at_level(logging.INFO, logger="pptx_generator.pipeline"):
        runner.execute(context)

    job_short = context.job_id[:8]
    tx_short = context.transaction_id[:8]
    assert any(job_short in rec.message and tx_short in rec.message for rec in caplog.records)
