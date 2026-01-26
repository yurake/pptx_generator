from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from pptx_generator.cli_commands import (
    create_compose_command,
    create_gen_command,
    create_prepare_command,
    create_template_command,
)


def test_prepare_invokes_queue(monkeypatch, tmp_path: Path) -> None:
    called = {}

    def fake_run_job_sync(stage: str, func, job_id=None, transaction_id=None, worker_count=1):  # noqa: ANN001
        called["stage"] = stage
        called["job_id"] = job_id
        called["transaction_id"] = transaction_id
        called["result"] = func()
        return called["result"]

    class _PrepareResult:
        def __init__(self, base: Path) -> None:
            self.messages = []
            self.cards_path = base / "prepare_card.json"
            self.log_path = base / "prepare_log.json"
            self.ai_log_path = base / "prepare_ai_log.json"
            self.meta_path = base / "ai_generation_meta.json"
            self.story_outline_path = base / "prepare_story_outline.json"
            self.audit_path = base / "audit_log.json"

    def fake_run_prepare_command(config, dump_json):  # noqa: ANN001
        called["ran_handler"] = True
        return _PrepareResult(config.output_dir)

    monkeypatch.setattr("pptx_generator.cli_commands.prepare.run_job_sync", fake_run_job_sync)
    monkeypatch.setattr("pptx_generator.cli_commands.prepare.run_prepare_command", fake_run_prepare_command)

    command = create_prepare_command(
        default_output_dir=tmp_path / ".pptx/prepare",
        default_jobspec_path=tmp_path / "jobspec.json",
        prompts_dirname=tmp_path / ".pptx/template/prompts",
        slide_inputs_filename=Path("slide_inputs.md"),
    )

    command.callback(  # type: ignore[attr-defined]
        (),
        tmp_path / ".pptx/prepare",
        None,
        "static",
        None,
    )
    assert called["stage"] == "prepare"
    assert called["ran_handler"] is True


def test_template_invokes_queue(monkeypatch, tmp_path: Path) -> None:
    called = {}

    def fake_run_job_sync(stage: str, func, job_id=None, transaction_id=None, worker_count=1):  # noqa: ANN001
        called["stage"] = stage
        called["result"] = func()
        return called["result"]

    class _ExtractionStub:
        def __init__(self, base: Path) -> None:
            class _TemplateSpec:
                blueprint = None

            self.template_spec = _TemplateSpec()
            self.prompt_templates_dir = base
            self.jobspec_path = base / "jobspec.json"
            self.branding_path = base / "branding.json"
            self.prompt_templates_created = False
            self.template_release_path = None
            self.template_spec_path = base / "template_spec.json"

    class _TemplateResult:
        def __init__(self, base: Path) -> None:
            self.extraction = _ExtractionStub(base)
            self.release = True

    def fake_run_template_command(config):  # noqa: ANN001
        called["ran_handler"] = True
        return _TemplateResult(config.output_dir)

    monkeypatch.setattr("pptx_generator.cli_commands.template.run_job_sync", fake_run_job_sync)
    monkeypatch.setattr("pptx_generator.cli_commands.template.run_template_command", fake_run_template_command)

    template_path = tmp_path / "template.pptx"
    template_path.write_bytes(b"pptx")

    command = create_template_command(
        default_extract_output=tmp_path / ".pptx/template",
        default_release_output=tmp_path / ".pptx/release",
        default_mode="dynamic",
    )

    command.callback(  # type: ignore[attr-defined]
        template_path,
        tmp_path / ".pptx/template",
        "json",
        None,
        None,
        "dynamic",
        False,
        None,
        None,
        None,
        tmp_path / ".pptx/release",
        None,
        None,
        None,
        (),
        None,
        None,
        False,
        "slide",
        False,
        False,
    )
    assert called["stage"] == "template"
    assert called["ran_handler"] is True


def test_compose_invokes_queue(monkeypatch, tmp_path: Path) -> None:
    called = {}

    def fake_run_job_sync(stage: str, func, job_id=None, transaction_id=None, worker_count=1):  # noqa: ANN001
        called["stage"] = stage
        called["result"] = func()
        return called["result"]

    def fake_run_compose_command(config):  # noqa: ANN001
        called["ran_handler"] = True
        return object()

    monkeypatch.setattr("pptx_generator.cli_commands.compose.run_job_sync", fake_run_job_sync)
    monkeypatch.setattr("pptx_generator.cli_commands.compose.run_compose_command", fake_run_compose_command)

    spec_path = tmp_path / "spec.json"
    spec_path.write_text("{}", encoding="utf-8")
    prepare_cards = tmp_path / "prepare_card.json"
    prepare_cards.write_text("{}", encoding="utf-8")
    rules_path = tmp_path / "rules.json"
    rules_path.write_text("{}", encoding="utf-8")

    command = create_compose_command(
        default_appendix_limit=3,
        default_output_dir=tmp_path / ".pptx/compose",
        default_rules_path=rules_path,
        default_prepare_cards_path=prepare_cards,
        default_draft_filename="draft.json",
        default_approved_filename="approved.json",
        default_draft_log_filename="draft_log.json",
        default_draft_meta_filename="draft_meta.json",
        default_generate_ready_filename="generate_ready.json",
        default_generate_ready_meta_filename="generate_ready_meta.json",
    )

    command.callback(  # type: ignore[attr-defined]
        spec_path,
        None,
        None,
        3,
        None,
        False,
        tmp_path / ".pptx/compose",
        rules_path,
        prepare_cards,
        True,
        0.6,
        12,
    )
    assert called["stage"] == "compose"
    assert called["ran_handler"] is True


def test_gen_invokes_queue(monkeypatch, tmp_path: Path) -> None:
    called = {}

    def fake_run_job_sync(stage: str, func, job_id=None, transaction_id=None, worker_count=1):  # noqa: ANN001
        called["stage"] = stage
        called["result"] = func()
        return called["result"]

    class _ContextStub:
        def __init__(self, base: Path) -> None:
            self.artifacts = {"pptx_path": str(base / "proposal.pptx")}

    class _GenResult:
        def __init__(self, base: Path) -> None:
            self.context = _ContextStub(base)
            self.audit_path = None

    def fake_run_generate_command(config):  # noqa: ANN001
        called["ran_handler"] = True
        return _GenResult(config.output_dir)

    monkeypatch.setattr("pptx_generator.cli_commands.gen.run_job_sync", fake_run_job_sync)
    monkeypatch.setattr("pptx_generator.cli_commands.gen.run_generate_command", fake_run_generate_command)

    gr_path = tmp_path / "generate_ready.json"
    gr_path.write_text('{"meta": {"schema_version": "1.0", "template_source": "template"}, "slides": []}', encoding="utf-8")

    command = create_gen_command(
        default_output_dir=tmp_path / ".pptx/gen",
        default_pptx_name="proposal.pptx",
        default_rules_path=tmp_path / "rules.json",
        default_pdf_output="proposal.pdf",
        default_pdf_timeout=120,
        default_pdf_retries=1,
    )

    command.callback(  # type: ignore[attr-defined]
        gr_path,
        tmp_path / ".pptx/gen",
        "proposal.pptx",
        tmp_path / "rules.json",
        False,
        "both",
        "proposal.pdf",
        None,
        120,
        1,
        None,
        None,
        None,
        (),
        None,
        False,
        False,
    )
    assert called["stage"] == "gen"
    assert called["ran_handler"] is True
