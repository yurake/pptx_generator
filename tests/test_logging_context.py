from __future__ import annotations

import logging
from pathlib import Path

from pptx_generator.logging import (
    reset_current_request_id,
    reset_current_stage,
    set_current_request_id,
    set_current_stage,
)
from pptx_generator.logging import configure_root_logging
from pptx_generator.runtime.job_context import reset_current_job, set_current_job


def test_logging_context_filter_adds_ids(tmp_path: Path, capsys):
    job_token = set_current_job("job-12345678", "tx-abcdef12")
    stage_token = set_current_stage("prepare")
    request_token = set_current_request_id("req-9999abcd")

    try:
        configure_root_logging(level=logging.INFO, log_dir=tmp_path)
        logger = logging.getLogger("pptx_generator.test")
        logger.info("hello")
        for handler in logging.getLogger().handlers:
            handler.flush()
    finally:
        reset_current_job(job_token)
        reset_current_stage(stage_token)
        reset_current_request_id(request_token)

    captured = capsys.readouterr().out
    assert "job=job-1234" in captured
    assert "tx=tx-abcd" in captured
    assert "stage=prepare" in captured
    assert "req=req-9999" in captured

    file_text = (tmp_path / "out.log").read_text(encoding="utf-8")
    assert "hello" in file_text
    assert "job=job-1234" in file_text
