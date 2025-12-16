import json
import os
import sys
from pathlib import Path

import pytest

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


def test_load_hooks_and_stage_execution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base_dir = tmp_path / "external"
    monkeypatch.setattr("pptx_generator.cli_hooks.manager.EXTERNAL_ROOT", base_dir)

    tpl_dir = base_dir / "sample_tpl"
    tpl_dir.mkdir(parents=True)

    script = _make_hook_script(tpl_dir)
    output_file = tpl_dir / "result.json"
    _write_hooks_json(
        tpl_dir,
        {
            "stage": {
                "prepare": {
                    "command": sys.executable,
                    "args": [str(script)],
                    "env": {"HOOK_OUTPUT": str(output_file)},
                }
            }
        },
    )

    manager = load_hooks_for_template_id("sample_tpl")
    assert manager is not None

    executed, continue_default = manager.run_stage_hook(
        "prepare",
        env={"PPTX_STAGE": "prepare"},
    )
    assert executed is True
    assert continue_default is True
    assert output_file.exists()
    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert data["PPTX_STAGE"] == "prepare"
    assert data["HOOK_OUTPUT"] == str(output_file)


def test_run_slide_hooks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base_dir = tmp_path / "external"
    monkeypatch.setattr("pptx_generator.cli_hooks.manager.EXTERNAL_ROOT", base_dir)

    tpl_dir = base_dir / "demo"
    tpl_dir.mkdir(parents=True)

    script = _make_hook_script(tpl_dir)
    output_file = tpl_dir / "slide_env.json"
    _write_hooks_json(
        tpl_dir,
        {
            "slides": {
                "01_system-layout": {
                    "prepare": {
                        "command": sys.executable,
                        "args": [str(script)],
                        "env": {"HOOK_OUTPUT": str(output_file)},
                    }
                }
            }
        },
    )

    manager = load_hooks_for_template_id("demo")
    assert manager is not None

    contexts = [
        SlideContext(
            key="01_system-layout",
            index=1,
            slide_id="system_layout-01",
            layout="System Layout",
            extra_env={"CUSTOM": "1"},
        ),
        SlideContext(
            key="02_other",
            index=2,
            slide_id="other-02",
            layout="Other",
        ),
    ]
    executed = manager.run_slide_hooks(
        STAGE_PREPARE,
        slides=contexts,
        env={"PPTX_STAGE": STAGE_PREPARE, "PPTX_TEMPLATE_ID": "demo"},
    )
    assert executed is True
    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert data["PPTX_SLIDE_KEY"] == "01_system-layout"
    assert data["PPTX_SLIDE_ID"] == "system_layout-01"
    assert data["PPTX_SLIDE_LAYOUT"] == "System Layout"
    assert data["CUSTOM"] == "1"


def test_run_slide_hooks_filters_and_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    base_dir = tmp_path / "external"
    monkeypatch.setattr("pptx_generator.cli_hooks.manager.EXTERNAL_ROOT", base_dir)

    # prepare hook config with continue_default variance
    hook_true = HookCommandConfig(command="echo", continue_default=True)
    hook_false = HookCommandConfig(command="echo", continue_default=False)
    config = HookConfig(
        slide_hooks={
            "01_slide": SlideHookConfig(stage_hooks={STAGE_PREPARE: hook_true}),
            "02_slide": SlideHookConfig(stage_hooks={STAGE_PREPARE: hook_false}),
        }
    )
    manager = ExternalHookManager(template_id="demo", base_dir=base_dir, config=config)
    monkeypatch.setattr(manager, "_execute_hook", lambda hook, env: None)

    # fallback contexts (slides=[]) should synthesize from config keys
    executed = manager.run_slide_hooks(
        STAGE_PREPARE,
        slides=[],
        env={"PPTX_STAGE": STAGE_PREPARE},
        allow_fallback_context=True,
    )
    assert executed is True

    # filter: only continue_default=True should run
    executed_filtered = manager.run_slide_hooks(
        STAGE_PREPARE,
        slides=[],
        env={"PPTX_STAGE": STAGE_PREPARE},
        continue_default_filter=True,
        allow_fallback_context=True,
    )
    assert executed_filtered is True

    # filter: only continue_default=False should run
    executed_filtered_false = manager.run_slide_hooks(
        STAGE_PREPARE,
        slides=[],
        env={"PPTX_STAGE": STAGE_PREPARE},
        continue_default_filter=False,
        allow_fallback_context=True,
    )
    assert executed_filtered_false is True


def test_slide_contexts_from_blueprint(tmp_path: Path) -> None:
    blueprint_slides = [
        {
            "layout": "System Layout",
            "slide_id": "system_layout-01",
            "required": True,
            "intent_tags": ["opening"],
        },
        {
            "layout": "Agenda",
            "slide_id": "agenda-02",
            "required": False,
        },
    ]
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    prompt_file = prompts_dir / "01_system-layout.md"
    prompt_file.write_text("dummy", encoding="utf-8")

    contexts = slide_contexts_from_blueprint(blueprint_slides, prompts_dir=prompts_dir)
    assert len(contexts) == 2
    assert contexts[0].key == "01_system-layout"
    assert contexts[0].layout == "System Layout"
    assert contexts[0].slide_id == "system_layout-01"
    assert contexts[1].key == "agenda-02"
    assert contexts[1].layout == "Agenda"
    assert contexts[1].slide_id == "agenda-02"
*** End Patch