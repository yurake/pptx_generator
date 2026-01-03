from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from click.exceptions import Exit
from click.testing import CliRunner

from pptx_generator.cli_commands import prepare as cli_prepare
from pptx_generator.cli_commands.prepare import (
    build_stage_env,
    determine_primary_prepare_path,
    echo_prepare_outputs,
    execute_prepare_command,
    load_hook_manager_if_static,
    normalize_prepare_inputs,
    run_post_slide_hooks,
    run_pre_slide_hooks,
    run_stage_hook_if_needed,
)
from pptx_generator.cli_handlers import PrepareCommandError
from pptx_generator.cli_hooks import STAGE_PREPARE


def test_normalize_prepare_inputs_splits_and_strips() -> None:
    inputs = ("a.md, b.md", " c.md ,", "d.md")
    normalized = normalize_prepare_inputs(inputs)
    assert normalized == ["a.md", "b.md", "c.md", "d.md"]


def test_determine_primary_prepare_path_prefers_first_existing(tmp_path: Path) -> None:
    existing = tmp_path / "found.md"
    existing.write_text("x", encoding="utf-8")
    missing = tmp_path / "missing.md"
    primary = determine_primary_prepare_path([str(missing), str(existing)])
    assert primary == existing


def test_determine_primary_prepare_path_returns_none(tmp_path: Path) -> None:
    assert determine_primary_prepare_path([str(tmp_path / "nope.md")]) is None


def test_build_stage_env_sets_all_fields(tmp_path: Path) -> None:
    env = build_stage_env(
        mode="static",
        primary_prepare_path=tmp_path / "input.md",
        normalized_inputs=["foo", "bar"],
        output_dir=tmp_path / "out",
        jobspec_path=tmp_path / "jobspec.json",
        page_limit=5,
    )
    assert env["PPTX_STAGE"] == STAGE_PREPARE
    assert env["PPTX_PREPARE_PATH"].endswith("input.md")
    assert env["PPTX_PREPARE_INPUTS"].splitlines() == ["foo", "bar"]
    assert env["PPTX_PREPARE_OUTPUT_DIR"].endswith("out")
    assert env["PPTX_JOBSPEC_PATH"].endswith("jobspec.json")
    assert env["PPTX_MODE"] == "static"
    assert env["PPTX_PAGE_LIMIT"] == "5"


def test_run_stage_hook_if_needed_aborts_on_no_continue(capsys) -> None:
    class Hook:
        def run_stage_hook(self, stage: str, env: dict[str, str]) -> tuple[bool, bool]:
            assert stage == STAGE_PREPARE
            assert env["PPTX_STAGE"] == STAGE_PREPARE
            return True, False

    env = {"PPTX_STAGE": STAGE_PREPARE}
    should_continue = run_stage_hook_if_needed(
        hook_manager=Hook(),
        template_id="tpl",
        stage_env=env,
    )
    captured = capsys.readouterr()
    assert "[hooks] prepare stage executed via external hook" in captured.out
    assert should_continue is False


def test_run_stage_hook_if_needed_allows_when_no_hook() -> None:
    assert run_stage_hook_if_needed(hook_manager=None, template_id=None, stage_env={}) is True


def test_run_stage_hook_if_needed_continues_when_hook_allows() -> None:
    class Hook:
        def run_stage_hook(self, stage: str, env: dict[str, str]) -> tuple[bool, bool]:
            return True, True

    assert run_stage_hook_if_needed(hook_manager=Hook(), template_id="tpl", stage_env={}) is True


def test_run_pre_slide_hooks_builds_context(monkeypatch, tmp_path: Path) -> None:
    jobspec = tmp_path / "jobspec.json"
    spec_dir = tmp_path / "extract"
    spec_dir.mkdir(parents=True, exist_ok=True)
    template_spec = spec_dir / "template_spec.json"
    template_spec.write_text('{"blueprint":{"slides":[{"id":"slide-1"}]}}', encoding="utf-8")
    jobspec.write_text(
        '{"meta":{"template_spec_path":"extract/template_spec.json","template_id":"demo"}}',
        encoding="utf-8",
    )

    called = {}

    def fake_slide_contexts(slides, prompts_dir=None):
        called["slides"] = slides
        called["prompts_dir"] = prompts_dir
        return [{"id": "slide-1"}]

    class Hook:
        def run_slide_hooks(self, stage, *, slides, env, continue_default_filter, allow_fallback_context):
            called["stage"] = stage
            called["env"] = env
            called["continue_default_filter"] = continue_default_filter
            called["allow_fallback_context"] = allow_fallback_context
            return False

    monkeypatch.setattr(cli_prepare, "slide_contexts_from_blueprint", fake_slide_contexts)
    contexts, executed = run_pre_slide_hooks(
        hook_manager=Hook(),
        template_id="demo",
        jobspec_path=jobspec,
        stage_env={"PPTX_STAGE": STAGE_PREPARE},
    )

    assert executed is False
    assert contexts == [{"id": "slide-1"}]
    assert called["stage"] == STAGE_PREPARE
    assert called["continue_default_filter"] is False
    assert called["allow_fallback_context"] is True


def test_run_pre_slide_hooks_warns_when_no_contexts(monkeypatch, tmp_path: Path, capsys) -> None:
    jobspec = tmp_path / "jobspec.json"
    jobspec.write_text("{}", encoding="utf-8")

    class Hook:
        def run_slide_hooks(self, stage, *, slides, env, continue_default_filter, allow_fallback_context):
            assert slides == []
            return False

    contexts, executed = run_pre_slide_hooks(
        hook_manager=Hook(),
        template_id="demo",
        jobspec_path=jobspec,
        stage_env={},
    )

    captured = capsys.readouterr()
    assert "[hooks] no slide contexts resolved" in captured.out
    assert contexts == []
    assert executed is False


def test_run_pre_slide_hooks_no_hook_returns_empty() -> None:
    contexts, executed = run_pre_slide_hooks(
        hook_manager=None,
        template_id=None,
        jobspec_path=Path("missing.json"),
        stage_env={},
    )
    assert contexts == []
    assert executed is False


def test_execute_prepare_command_wraps_prepare_error(monkeypatch) -> None:
    def fake_run_job_sync(*, stage, func):
        raise PrepareCommandError("failed", exit_code=7)

    monkeypatch.setattr(cli_prepare, "run_job_sync", fake_run_job_sync)

    with pytest.raises(Exit) as exc_info:
        execute_prepare_command(SimpleNamespace())

    assert exc_info.value.exit_code == 7


def test_echo_prepare_outputs_prints_all(capsys, tmp_path: Path) -> None:
    result = SimpleNamespace(
        messages=["m1", "m2"],
        cards_path=tmp_path / "cards.json",
        log_path=tmp_path / "log.json",
        ai_log_path=tmp_path / "ai_log.json",
        meta_path=tmp_path / "meta.json",
        story_outline_path=tmp_path / "story.json",
        audit_path=tmp_path / "audit.json",
    )

    echo_prepare_outputs(result)
    output = capsys.readouterr().out
    assert "m1" in output and "m2" in output
    assert "Prepare Card" in output
    assert "Audit Log" in output


def test_run_post_slide_hooks_injects_outputs(tmp_path: Path) -> None:
    captured: dict[str, str] = {}

    class Hook:
        def run_slide_hooks(self, stage, *, slides, env, continue_default_filter, allow_fallback_context):
            captured.update(env)
            assert continue_default_filter is True
            assert allow_fallback_context is True
            return False

    result = SimpleNamespace(
        cards_path=tmp_path / "cards.json",
        log_path=tmp_path / "log.json",
        ai_log_path=tmp_path / "ai_log.json",
        meta_path=tmp_path / "meta.json",
        story_outline_path=tmp_path / "story.json",
        audit_path=tmp_path / "audit.json",
    )

    run_post_slide_hooks(
        hook_manager=Hook(),
        template_id="demo",
        stage_env={"PPTX_STAGE": STAGE_PREPARE},
        contexts=[{"id": "slide-1"}],
        result=result,
    )

    assert captured["PPTX_PREPARE_CARD_PATH"].endswith("cards.json")
    assert captured["PPTX_PREPARE_AUDIT_PATH"].endswith("audit.json")


def test_run_post_slide_hooks_no_hook_noop() -> None:
    run_post_slide_hooks(
        hook_manager=None,
        template_id=None,
        stage_env={},
        contexts=[],
        result=SimpleNamespace(),
    )


def test_load_hook_manager_if_static_adds_template(monkeypatch, tmp_path: Path) -> None:
    jobspec = tmp_path / "jobspec.json"
    jobspec.write_text('{"meta":{"template_id":"demo"}}', encoding="utf-8")

    class Hook:
        pass

    monkeypatch.setattr(cli_prepare, "load_hooks_for_template_id", lambda tpl: Hook())
    stage_env = {"PPTX_STAGE": STAGE_PREPARE}

    hook_manager, template_id = load_hook_manager_if_static(
        mode="static",
        jobspec_path=jobspec,
        stage_env=stage_env,
    )

    assert isinstance(hook_manager, Hook)
    assert template_id == "demo"
    assert stage_env["PPTX_TEMPLATE_ID"] == "demo"


def test_prepare_command_runs_dynamic_flow(monkeypatch, tmp_path: Path) -> None:
    prepared = {}

    class Result(SimpleNamespace):
        messages = ["done"]
        cards_path = tmp_path / "cards.json"
        log_path = tmp_path / "log.json"
        ai_log_path = tmp_path / "ai_log.json"
        meta_path = tmp_path / "meta.json"
        story_outline_path = tmp_path / "story.json"
        audit_path = tmp_path / "audit.json"

    def fake_run_prepare_command(config, dump_json):  # type: ignore[missing-annotations]
        prepared["config"] = config
        return Result()

    monkeypatch.setattr(cli_prepare, "run_prepare_command", fake_run_prepare_command)
    monkeypatch.setattr(cli_prepare, "run_job_sync", lambda stage, func: func())

    command = cli_prepare.create_prepare_command(
        default_output_dir=tmp_path / "out",
        default_jobspec_path=tmp_path / "jobspec.json",
        prompts_dirname=Path("prompts"),
        slide_inputs_filename=Path("prepare_card.json"),
    )

    result = CliRunner().invoke(
        command,
        [
            str(tmp_path / "input-a.md"),
            "input-b.md",
            "--mode",
            "dynamic",
            "--output",
            str(tmp_path / "out"),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert prepared["config"].mode == "dynamic"
    assert prepared["config"].prepare_inputs[0].endswith("input-a.md")
    assert prepared["config"].prepare_inputs[1] == "input-b.md"


def test_prepare_command_exits_when_pre_slide_hook_executed(monkeypatch, tmp_path: Path) -> None:
    prepared: dict[str, object] = {}
    command = cli_prepare.create_prepare_command(
        default_output_dir=tmp_path / "out",
        default_jobspec_path=tmp_path / "jobspec.json",
        prompts_dirname=Path("prompts"),
        slide_inputs_filename=Path("prepare_card.json"),
    )

    jobspec = tmp_path / "jobspec.json"
    jobspec.parent.mkdir(parents=True, exist_ok=True)
    jobspec.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(cli_prepare, "normalize_prepare_inputs", lambda inputs: list(inputs))
    monkeypatch.setattr(cli_prepare, "determine_primary_prepare_path", lambda inputs: None)
    monkeypatch.setattr(cli_prepare, "build_stage_env", lambda **kwargs: {})
    monkeypatch.setattr(cli_prepare, "load_hook_manager_if_static", lambda **kwargs: ("hooks", "tpl"))
    monkeypatch.setattr(cli_prepare, "run_stage_hook_if_needed", lambda **kwargs: True)
    monkeypatch.setattr(cli_prepare, "build_prepare_config", lambda **kwargs: None)
    monkeypatch.setattr(cli_prepare, "run_pre_slide_hooks", lambda **kwargs: ([], True))
    monkeypatch.setattr(cli_prepare, "run_prepare_command", lambda *args, **kwargs: prepared.setdefault("called", True))

    result = CliRunner().invoke(
        command,
        [
            "input-a.md",
            "--mode",
            "static",
            "--jobspec",
            str(jobspec),
            "--output",
            str(tmp_path / "out"),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "called" not in prepared


def test_prepare_command_aborts_when_stage_hook_blocks(monkeypatch, tmp_path: Path) -> None:
    prepared: dict[str, object] = {}
    command = cli_prepare.create_prepare_command(
        default_output_dir=tmp_path / "out",
        default_jobspec_path=tmp_path / "jobspec.json",
        prompts_dirname=Path("prompts"),
        slide_inputs_filename=Path("prepare_card.json"),
    )

    jobspec = tmp_path / "jobspec.json"
    jobspec.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(cli_prepare, "normalize_prepare_inputs", lambda inputs: list(inputs))
    monkeypatch.setattr(cli_prepare, "determine_primary_prepare_path", lambda inputs: None)
    monkeypatch.setattr(cli_prepare, "build_stage_env", lambda **kwargs: {})
    monkeypatch.setattr(cli_prepare, "load_hook_manager_if_static", lambda **kwargs: ("hooks", "tpl"))
    monkeypatch.setattr(cli_prepare, "run_stage_hook_if_needed", lambda **kwargs: False)
    monkeypatch.setattr(cli_prepare, "run_prepare_command", lambda *args, **kwargs: prepared.setdefault("called", True))

    result = CliRunner().invoke(
        command,
        [
            "input-a.md",
            "--mode",
            "static",
            "--jobspec",
            str(jobspec),
            "--output",
            str(tmp_path / "out"),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "called" not in prepared
