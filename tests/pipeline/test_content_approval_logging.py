from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from pptx_generator.pipeline.content_approval import ContentApprovalStep, ContentApprovalOptions, ContentApprovalError
from pptx_generator.pipeline.base import PipelineContext, PipelineArtifacts
from pptx_generator.models import JobSpec, JobMeta, JobAuth


def _make_context(tmp_path: Path) -> PipelineContext:
    meta = JobMeta(schema_version="1.0", title="t")
    auth = JobAuth(created_by="tester")
    spec = JobSpec(meta=meta, auth=auth, slides=[])
    ctx = PipelineContext(spec=spec, workdir=tmp_path, artifacts=PipelineArtifacts())
    return ctx


def test_content_approval_missing_required_logs_error(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    ctx = _make_context(tmp_path)
    step = ContentApprovalStep(ContentApprovalOptions(approved_path=None, require_document=True))
    caplog.clear()
    with caplog.at_level(logging.ERROR):
        with pytest.raises(ContentApprovalError):
            step.run(ctx)
    assert any("content_approval failed" in msg for msg in caplog.messages)


def test_content_approval_loaded_logs_info(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    ctx = _make_context(tmp_path)
    approved_path = tmp_path / "approved.json"
    approved_path.write_text('{"slides": [], "meta": {}}', encoding="utf-8")
    step = ContentApprovalStep(ContentApprovalOptions(approved_path=approved_path, require_document=True))
    caplog.clear()
    with caplog.at_level(logging.INFO):
        step.run(ctx)
    assert any("content_approval completed" in msg for msg in caplog.messages)
