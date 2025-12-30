from __future__ import annotations

from pathlib import Path

from pptx_generator.api import stages


def test_build_compose_job_uses_draft_dir_constant(tmp_path, monkeypatch):
    captured = {}

    def fake_run_compose_command(config):
        captured["config"] = config
        return "ok"

    monkeypatch.setattr(stages, "run_compose_command", fake_run_compose_command)

    workdir = tmp_path
    template_artifacts = {
        "jobspec_url": workdir / "jobspec.json",
        "diagnostics_url": workdir / "diag.json",
    }
    prepare_artifacts = {"prepare_card_url": workdir / "prepare_card.json"}

    job = stages.build_compose_job({}, workdir, template_artifacts, prepare_artifacts)
    result = job()

    config = captured["config"]
    assert config.draft_output.name == stages.DRAFT_DIRNAME
    assert result["artifacts"]["draft_mapping_log_url"].startswith(str(workdir / stages.DRAFT_DIRNAME))
    assert result["artifacts"]["draft_review_log_url"].startswith(str(workdir / stages.DRAFT_DIRNAME))
