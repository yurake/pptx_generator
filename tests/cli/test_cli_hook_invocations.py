from __future__ import annotations

from pathlib import Path
from typing import Any

import click
from click.testing import CliRunner

from pptx_generator.cli_commands.compose import create_compose_command
from pptx_generator.cli_commands.gen import create_gen_command
from pptx_generator.cli_commands.mapping import create_mapping_command
from pptx_generator.cli_commands.prepare import create_prepare_command
from pptx_generator.cli_commands.template import create_template_command
from pptx_generator.cli_hooks.manager import SlideContext


class DummyHookManager:
    def __init__(self) -> None:
        self.stage_calls: list[tuple[str, dict[str, str]]] = []
        self.slide_calls: list[dict[str, Any]] = []

    def run_stage_hook(self, stage: str, env: dict[str, str]) -> tuple[bool, bool]:
        self.stage_calls.append((stage, dict(env)))
        return True, True

    def run_slide_hooks(
        self,
        stage: str,
        *,
        slides: list[SlideContext] | list[dict[str, Any]],
        env: dict[str, str],
        continue_default_filter: bool | None = None,
        allow_fallback_context: bool = False,
    ) -> bool:
        self.slide_calls.append(
            {
                "stage": stage,
                "slides": slides,
                "env": dict(env),
                "continue_default_filter": continue_default_filter,
                "allow_fallback_context": allow_fallback_context,
            }
        )
        return False


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")
    return path


def test_prepare_invokes_slide_hooks_with_fallback(monkeypatch, tmp_path: Path) -> None:
    hook_manager = DummyHookManager()

    monkeypatch.setattr("pptx_generator.cli_commands.prepare.load_hooks_for_template_id", lambda tpl: hook_manager)
    monkeypatch.setattr(
        "pptx_generator.cli_commands.prepare.extract_template_id_from_json_file",
        lambda path: "demo_tpl",
    )
    monkeypatch.setattr(
        "pptx_generator.cli_commands.prepare.slide_contexts_from_blueprint",
        lambda *args, **kwargs: [],
    )

    class Result:
        def __init__(self, base: Path) -> None:
            self.cards_path = _touch(base / "cards.json")
            self.log_path = _touch(base / "log.json")
            self.ai_log_path = _touch(base / "ai_log.json")
            self.meta_path = _touch(base / "meta.json")
            self.story_outline_path = _touch(base / "story.json")
            self.audit_path = _touch(base / "audit.json")
            self.messages = ["ok"]

    monkeypatch.setattr(
        "pptx_generator.cli_commands.prepare.run_prepare_command",
        lambda config, dump_json: Result(tmp_path / "out"),
    )

    cmd = create_prepare_command(
        default_output_dir=tmp_path / "out",
        default_jobspec_path=_touch(tmp_path / "jobspec.json"),
        prompts_dirname=Path("prompts"),
        slide_inputs_filename=Path("prepare_card.json"),
    )

    jobspec = tmp_path / "jobspec.json"
    jobspec.write_text('{"meta":{"template_id":"demo_tpl","template_spec_path":""}}', encoding="utf-8")
    prepare_input = _touch(tmp_path / "input.md")

    result = CliRunner().invoke(
        cmd,
        [
            str(prepare_input),
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

    assert hook_manager.slide_calls
    pre_call = hook_manager.slide_calls[0]
    post_call = hook_manager.slide_calls[-1]
    assert pre_call["allow_fallback_context"] is True
    assert pre_call["continue_default_filter"] is False
    assert post_call["allow_fallback_context"] is True
    assert post_call["continue_default_filter"] is True


def test_mapping_invokes_slide_hooks_with_fallback(monkeypatch, tmp_path: Path) -> None:
    hook_manager = DummyHookManager()
    monkeypatch.setattr(
        "pptx_generator.cli_commands.mapping.load_stage_hooks",
        lambda path: (hook_manager, "demo_tpl"),
    )
    monkeypatch.setattr(
        "pptx_generator.cli_commands.mapping.slide_contexts_from_generate_ready",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr("pptx_generator.cli_commands.mapping.run_mapping_command", lambda config: type("R", (), {"context": None})())
    monkeypatch.setattr("pptx_generator.cli_commands.mapping.echo_mapping_outputs", lambda context: None)

    cmd = create_mapping_command(
        default_output_dir=tmp_path / "out",
        default_rules_path=_touch(tmp_path / "pipeline_rules.json"),
        default_prepare_cards_path=_touch(tmp_path / "prepare_card.json"),
    )

    spec = _touch(tmp_path / "spec.json")
    result = CliRunner().invoke(
        cmd,
        [
            str(spec),
            "--output",
            str(tmp_path / "out"),
            "--rules",
            str(tmp_path / "pipeline_rules.json"),
            "--prepare-cards",
            str(tmp_path / "prepare_card.json"),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    assert hook_manager.slide_calls
    pre_call = hook_manager.slide_calls[0]
    post_call = hook_manager.slide_calls[-1]
    assert pre_call["allow_fallback_context"] is True
    assert pre_call["continue_default_filter"] is False
    assert post_call["allow_fallback_context"] is True
    assert post_call["continue_default_filter"] is True


def test_compose_invokes_slide_hooks_with_fallback(monkeypatch, tmp_path: Path) -> None:
    hook_manager = DummyHookManager()
    monkeypatch.setattr(
        "pptx_generator.cli_commands.compose.load_stage_hooks",
        lambda path: (hook_manager, "demo_tpl"),
    )
    monkeypatch.setattr(
        "pptx_generator.cli_commands.compose.slide_contexts_from_generate_ready",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr("pptx_generator.cli_commands.compose.run_compose_command", lambda config: None)

    cmd = create_compose_command(
        default_appendix_limit=0,
        default_output_dir=tmp_path / "out",
        default_rules_path=_touch(tmp_path / "pipeline_rules.json"),
        default_prepare_cards_path=_touch(tmp_path / "prepare_card.json"),
        default_draft_filename="draft.json",
        default_approved_filename="approved.json",
        default_draft_log_filename="draft_log.json",
        default_draft_meta_filename="draft_meta.json",
        default_generate_ready_filename="generate_ready.json",
        default_generate_ready_meta_filename="generate_ready_meta.json",
    )

    spec = _touch(tmp_path / "spec.json")
    result = CliRunner().invoke(
        cmd,
        [
            str(spec),
            "--output",
            str(tmp_path / "out"),
            "--rules",
            str(tmp_path / "pipeline_rules.json"),
            "--prepare-cards",
            str(tmp_path / "prepare_card.json"),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    assert hook_manager.slide_calls
    pre_call = hook_manager.slide_calls[0]
    post_call = hook_manager.slide_calls[-1]
    assert pre_call["allow_fallback_context"] is True
    assert pre_call["continue_default_filter"] is False
    assert post_call["allow_fallback_context"] is True
    assert post_call["continue_default_filter"] is True


def test_gen_invokes_slide_hooks_with_fallback(monkeypatch, tmp_path: Path) -> None:
    hook_manager = DummyHookManager()
    monkeypatch.setattr("pptx_generator.cli_commands.gen.load_hooks_for_template_id", lambda tpl: hook_manager)
    monkeypatch.setattr(
        "pptx_generator.cli_commands.gen.extract_template_id_from_json_file",
        lambda path: "demo_tpl",
    )
    monkeypatch.setattr(
        "pptx_generator.cli_commands.gen.slide_contexts_from_generate_ready",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr("pptx_generator.cli_commands.gen.run_generate_command", lambda config: type("R", (), {"context": None, "audit_path": tmp_path / 'audit.json'})())
    monkeypatch.setattr("pptx_generator.cli_commands.gen.echo_render_outputs", lambda context, audit_path: None)

    cmd = create_gen_command(
        default_output_dir=tmp_path / "out",
        default_pptx_name="out.pptx",
        default_rules_path=_touch(tmp_path / "pipeline_rules.json"),
        default_pdf_output="out.pdf",
        default_pdf_timeout=10,
        default_pdf_retries=1,
    )

    generate_ready = _touch(tmp_path / "generate_ready.json")
    result = CliRunner().invoke(
        cmd,
        [
            str(generate_ready),
            "--output",
            str(tmp_path / "out"),
            "--pptx-name",
            "out.pptx",
            "--rules",
            str(tmp_path / "pipeline_rules.json"),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    assert hook_manager.slide_calls
    pre_call = hook_manager.slide_calls[0]
    post_call = hook_manager.slide_calls[-1]
    assert pre_call["allow_fallback_context"] is True
    assert pre_call["continue_default_filter"] is False
    assert post_call["allow_fallback_context"] is True
    assert post_call["continue_default_filter"] is True


def test_template_invokes_slide_hooks_with_fallback(monkeypatch, tmp_path: Path) -> None:
    hook_manager = DummyHookManager()
    monkeypatch.setattr("pptx_generator.cli_commands.template.load_hooks_for_template_id", lambda tpl: hook_manager)
    monkeypatch.setattr("pptx_generator.cli_commands.template.ensure_hook_skeleton", lambda tpl, keys: None)
    monkeypatch.setattr(
        "pptx_generator.cli_commands.template.slide_contexts_from_blueprint",
        lambda *args, **kwargs: [SlideContext(key="01_demo", index=1)],
    )

    class Extraction:
        def __init__(self, base: Path) -> None:
            class _Slide:
                @staticmethod
                def model_dump(*args: Any, **kwargs: Any) -> dict[str, str]:
                    return {"dummy": "1"}

            class _Blueprint:
                def __init__(self) -> None:
                    self.slides = [self._slide]

                _slide = _Slide()

            blueprint = _Blueprint()
            self.template_spec = type("Spec", (), {"blueprint": blueprint})
            self.prompt_templates_dir = base / "prompts"
            self.prompt_templates_dir.mkdir(parents=True, exist_ok=True)
            self.prompt_templates_created = 1
            self.template_spec_path = _touch(base / "template_spec.json")
            self.jobspec_path = _touch(base / "jobspec.json")
            self.branding_path = _touch(base / "branding.json")

    class Result:
        def __init__(self, base: Path) -> None:
            self.extraction = Extraction(base)
            self.release = None

    monkeypatch.setattr("pptx_generator.cli_commands.template.run_template_command", lambda config: Result(tmp_path / "out"))
    monkeypatch.setattr(
        "pptx_generator.cli_commands.template.derive_template_id_from_template_path",
        lambda path: "demo_tpl",
    )

    cmd = create_template_command(
        default_extract_output=tmp_path / "out",
        default_release_output=tmp_path / "release",
        default_mode="static",
        default_template_ai_policy=None,
    )

    template_path = _touch(tmp_path / "template.pptx")
    result = CliRunner().invoke(
        cmd,
        [
            str(template_path),
            "--mode",
            "static",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0

    assert hook_manager.slide_calls
    call = hook_manager.slide_calls[-1]
    assert call["allow_fallback_context"] is True
    assert call["continue_default_filter"] is True
