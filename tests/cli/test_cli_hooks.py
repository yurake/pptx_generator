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
