from __future__ import annotations

from pptx_generator.cli_commands.hook_runner import run_stage_hook


class DummyHookManager:
    def __init__(self, executed: bool, continue_default: bool) -> None:
        self.executed = executed
        self.continue_default = continue_default
        self.calls: list[dict[str, object]] = []

    def run_stage_hook(self, stage: str, env: dict[str, str]) -> tuple[bool, bool]:
        self.calls.append({"stage": stage, "env": dict(env)})
        return self.executed, self.continue_default


def test_run_stage_hook_respects_continue_default_false(capsys) -> None:
    hook_manager = DummyHookManager(executed=True, continue_default=False)
    stage_env = {"PPTX_STAGE": "compose"}

    should_skip_default = run_stage_hook(
        "compose",
        hook_manager=hook_manager,
        template_id="tpl",
        stage_env=stage_env,
    )

    assert should_skip_default is True
    out = capsys.readouterr().out
    assert "[hooks] compose stage executed via external hook" in out


def test_run_stage_hook_respects_continue_default_true(capsys) -> None:
    hook_manager = DummyHookManager(executed=True, continue_default=True)
    stage_env = {"PPTX_STAGE": "mapping"}

    should_skip_default = run_stage_hook(
        "mapping",
        hook_manager=hook_manager,
        template_id="tpl",
        stage_env=stage_env,
    )

    assert should_skip_default is False
    out = capsys.readouterr().out
    assert "[hooks] mapping stage executed via external hook" in out


def test_run_stage_hook_no_execution_returns_false(capsys) -> None:
    hook_manager = DummyHookManager(executed=False, continue_default=False)
    stage_env = {"PPTX_STAGE": "gen"}

    should_skip_default = run_stage_hook(
        "gen",
        hook_manager=hook_manager,
        template_id=None,
        stage_env=stage_env,
    )

    assert should_skip_default is False
    out = capsys.readouterr().out
    assert out == ""
