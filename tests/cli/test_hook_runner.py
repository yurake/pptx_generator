from __future__ import annotations

import pytest

from pptx_generator.cli_commands.hook_runner import (
    load_stage_hooks,
    run_post_stage_slide_hooks,
    run_stage_hook,
)


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


def test_load_stage_hooks_propagates_exceptions(monkeypatch, tmp_path) -> None:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text("{}", encoding="utf-8")

    def boom(path):  # noqa: ANN001
        raise ValueError("bad json")

    monkeypatch.setattr(
        "pptx_generator.cli_commands.hook_runner.extract_template_id_from_json_file",
        boom,
    )

    with pytest.raises(ValueError):
        load_stage_hooks(spec_path)


def test_load_stage_hooks_returns_none_for_missing_template(monkeypatch, tmp_path) -> None:
    spec_path = tmp_path / "spec.json"
    spec_path.write_text("{}", encoding="utf-8")

    hook_manager, template_id = load_stage_hooks(spec_path)

    assert hook_manager is None
    assert template_id is None


def test_run_post_stage_slide_hooks_propates_loader_error(tmp_path) -> None:
    class DummyHM:
        def run_slide_hooks(self, *_, **__):  # noqa: ANN001, ARG002
            return False

    hook_manager = DummyHM()
    generate_ready_path = tmp_path / "missing.json"

    def loader(path):  # noqa: ANN001
        raise RuntimeError("loader failed")

    with pytest.raises(RuntimeError):
        run_post_stage_slide_hooks(
            "compose",
            hook_manager=hook_manager,
            template_id="tpl",
            base_stage_env={"PPTX_STAGE": "compose"},
            generate_ready_path=generate_ready_path,
            slide_context_loader=loader,
        )


def test_run_post_stage_slide_hooks_passes_resolved_path(tmp_path) -> None:
    calls = {}

    class DummyHM:
        def run_slide_hooks(self, stage, slides, env, **kwargs):  # noqa: ANN001
            calls["stage"] = stage
            calls["slides"] = list(slides)
            calls["env"] = dict(env)
            calls["kwargs"] = kwargs
            return False

    hook_manager = DummyHM()
    generate_ready_path = tmp_path / "missing.json"

    def loader(path):  # noqa: ANN001
        calls["loader_path"] = path
        return []

    run_post_stage_slide_hooks(
        "mapping",
        hook_manager=hook_manager,
        template_id="tpl",
        base_stage_env={"PPTX_STAGE": "mapping", "NESTED": {"x": 1}},
        generate_ready_path=generate_ready_path,
        slide_context_loader=loader,
    )

    assert calls["stage"] == "mapping"
    assert calls["loader_path"] == generate_ready_path
    assert calls["env"]["PPTX_GENERATE_READY_PATH"] == str(generate_ready_path.resolve())
