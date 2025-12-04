from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from pptx_generator.cli_hooks import (
    EXTERNAL_ROOT,
    STAGE_PREPARE,
    build_slide_key,
    derive_template_id_from_template_path,
    extract_template_id_from_json_file,
    load_hooks_for_template_id,
    slide_contexts_from_blueprint,
    slide_contexts_from_generate_ready,
)
from pptx_generator.cli_hooks.manager import SlideContext


def _make_hook_script(path: Path) -> Path:
    script = path / "hook.py"
    script.write_text(
        "\n".join(
            [
                "import json",
                "import os",
                "from pathlib import Path",
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
    assert continue_default is False
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
    first = contexts[0]
    assert first.key == "01_system-layout"
    assert first.extra_env["PPTX_SLIDE_REQUIRED"] == "1"
    assert "PPTX_PROMPT_TEMPLATE_PATH" in first.extra_env
    second = contexts[1]
    assert second.key == "02_agenda"
    assert second.extra_env["PPTX_SLIDE_REQUIRED"] == "0"


def test_slide_contexts_from_generate_ready(tmp_path: Path) -> None:
    generate_ready = tmp_path / "generate_ready.json"
    generate_ready.write_text(
        json.dumps(
            {
                "slides": [
                    {
                        "layout_id": "system_layout",
                        "meta": {"page_no": 1, "blueprint_slide_id": "system_layout-01"},
                    },
                    {
                        "layout_name": "closing",
                        "meta": {"page_no": 5, "sources": ["closing-05"]},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    contexts = slide_contexts_from_generate_ready(generate_ready)
    assert [ctx.key for ctx in contexts] == ["01_system-layout", "05_closing"]


def test_template_id_helpers(tmp_path: Path) -> None:
    tpl_path = tmp_path / "テンプレート_v1.pptx"
    tpl_path.write_text("", encoding="utf-8")
    assert derive_template_id_from_template_path(tpl_path) == "テンプレート_v1"

    jobspec = tmp_path / "jobspec.json"
    jobspec.write_text(json.dumps({"meta": {"template_id": "demo_tpl"}}), encoding="utf-8")
    assert extract_template_id_from_json_file(jobspec) == "demo_tpl"


def test_build_slide_key() -> None:
    assert build_slide_key(1, "System Layout", None) == "01_system-layout"
    assert build_slide_key(12, None, "custom-id") == "12_custom-id"
