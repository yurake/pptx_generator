import json
import os
import sys
import subprocess
from pathlib import Path

import pytest

from pptx_generator.cli_hooks import slide_contexts_from_blueprint
from pptx_generator.cli_hooks.manager import (
    STAGE_PREPARE,
    HookCommandConfig,
    HookConfig,
    SlideContext,
    SlideHookConfig,
    ExternalHookManager,
    load_hooks_for_template_id,
)


def _make_hook_script(base_dir: Path) -> Path:
    script = base_dir / "hook.py"
    script.write_text(
        "\n".join(
            [
                "import json",
                "import os",
                "from pathlib import Path",
                "",
                "output = Path(os.environ['HOOK_OUTPUT'])",
                "output.write_text(json.dumps(dict(os.environ), ensure_ascii=False))",
            ]
        ),
        encoding="utf-8",
    )
    return script


def _write_hooks_json(path: Path, payload: dict) -> Path:
    config_path = path / "hooks.json"
    config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return config_path


def test_load_hooks_for_template_id(monkeypatch, tmp_path: Path) -> None:
    external_root = tmp_path / "external"
    external_root.mkdir()
    template_dir = external_root / tmp_path.name
    template_dir.mkdir()

    config_path = _write_hooks_json(
        template_dir,
        {
            "stage": {
                "compose": {
                    "command": sys.executable,
                    "args": ["-c", "print('compose')"],
                }
            },
            "slides": {
                "title": {
                    "gen": {
                        "command": sys.executable,
                        "args": ["-c", "print('gen')"],
                    }
                }
            },
        },
    )

    monkeypatch.chdir(tmp_path)

    manager = load_hooks_for_template_id(tmp_path.name)

    assert manager is not None
    assert template_dir.resolve() == manager.base_dir.resolve()
    assert manager.config.slide_hooks


# ... existing tests ...

def test_execute_hook_raises_runtime(monkeypatch, tmp_path: Path) -> None:
    def fake_run(self, *, cwd, extra_env=None):  # noqa: ANN001, ARG002
        raise subprocess.CalledProcessError(1, "cmd", output="out", stderr="err")

    hook = HookCommandConfig(command="echo")
    monkeypatch.setattr(HookCommandConfig, "run", fake_run)

    manager = ExternalHookManager(template_id="demo", base_dir=tmp_path, config=HookConfig())

    with pytest.raises(RuntimeError):
        manager._execute_hook(hook, {})


def test_run_slide_hooks_fallback_and_filters(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    calls: list[str] = []

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stdout="", stderr=""),
    )
    manager = ExternalHookManager(
        template_id="demo",
        base_dir=tmp_path,
        config=HookConfig(
            slide_hooks={
                "s1": SlideHookConfig(stage_hooks={"prepare": HookCommandConfig(command="echo", continue_default=True)}),
                "s2": SlideHookConfig(
                    stage_hooks={"prepare": HookCommandConfig(command="echo", continue_default=False)}
                ),
            }
        ),
    )
    monkeypatch.setattr(
        ExternalHookManager,
        "_execute_hook",
        lambda self, hook, env: calls.append(env["PPTX_SLIDE_KEY"]),
    )

    executed_true = manager.run_slide_hooks(
        STAGE_PREPARE,
        slides=[],
        env={},
        continue_default_filter=True,
        allow_fallback_context=True,
    )
    assert executed_true is True
    assert calls == ["s1"]

    calls.clear()
    manager._synced_once = False
    executed_false = manager.run_slide_hooks(
        STAGE_PREPARE,
        slides=[],
        env={},
        continue_default_filter=False,
        allow_fallback_context=True,
    )
    assert executed_false is True
    assert calls == ["s2"]


def test_load_hook_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ExternalHookManager._load_hook(ExternalHookManager, tmp_path / "missing.json")


def test_ensure_project_dir_creates(tmp_path: Path) -> None:
    base_dir = tmp_path / "not-exist"
    manager = ExternalHookManager(template_id="demo", base_dir=base_dir, config=HookConfig())
    manager._ensure_project_dir()
    assert base_dir.exists()


def test_log_subprocess_output(caplog) -> None:
    caplog.set_level("INFO")
    from pptx_generator.cli_hooks.manager import _log_subprocess_output  # local import for caplog

    _log_subprocess_output("demo", "out", "err")
    assert any("demo stdout" in record.message for record in caplog.records)
    assert any("demo stderr" in record.message for record in caplog.records)
