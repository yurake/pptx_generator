from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from pptx_generator.cli_handlers import (
    SLIDE_INPUTS_FILENAME,
    PrepareCommandConfig,
    PrepareCommandError,
    run_prepare_command,
)
from pptx_generator.cli_handlers.common import dump_json
from pptx_generator.cli_hooks import (
    STAGE_PREPARE,
    slide_contexts_from_blueprint,
    extract_template_id_from_json_file,
    load_hooks_for_template_id,
)


def build_prepare_config(
    *,
    prepare_path: Path | None,
    output_dir: Path,
    jobspec: Path | None,
    mode: str,
    page_limit: int | None,
    default_policy_path: Path,
    default_jobspec_path: Path,
    prompts_dirname: Path,
    slide_inputs_filename: Path,
) -> PrepareCommandConfig:
    return PrepareCommandConfig(
        prepare_path=prepare_path,
        output_dir=output_dir,
        jobspec_path=jobspec,
        mode=mode,
        page_limit=page_limit,
        policy_path=default_policy_path,
        default_jobspec_path=default_jobspec_path,
        prompts_dirname=prompts_dirname,
        slide_inputs_filename=slide_inputs_filename,
    )


def create_prepare_command(
    *,
    default_output_dir: Path,
    default_policy_path: Path,
    default_jobspec_path: Path,
    prompts_dirname: Path,
    slide_inputs_filename: Path = SLIDE_INPUTS_FILENAME,
) -> click.Command:
    @click.command("prepare")
    @click.argument(
        "prepare_path",
        type=click.Path(exists=True, dir_okay=False,
                        readable=True, path_type=Path),
        required=False,
    )
    @click.option(
        "--output",
        "-o",
        "output_dir",
        type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
        default=default_output_dir,
        show_default=True,
        help="コンテンツ準備成果物を保存するディレクトリ",
    )
    @click.option(
        "--mode",
        type=click.Choice(["dynamic", "static"], case_sensitive=False),
        required=True,
        help="カード生成モード。static は Blueprint を利用する",
    )
    @click.option(
        "--jobspec",
        type=click.Path(exists=True, dir_okay=False,
                        readable=True, path_type=Path),
        default=None,
        help="静的モードで参照する jobspec.json (未指定時は .pptx/extract/jobspec.json を探索)",
    )
    @click.option(
        "-p",
        "--page-limit",
        "--card-limit",
        type=click.IntRange(1, None),
        default=None,
        help="生成するカード枚数の上限",
    )
    def prepare(  # type: ignore[function-uses-closure]
        prepare_path: Path | None,
        output_dir: Path,
        jobspec: Path | None,
        mode: str,
        page_limit: int | None,
    ) -> None:
        """stage 2 コンテンツ準備: PrepareCard 成果物を生成する。"""

        jobspec_path = jobspec or default_jobspec_path
        hook_manager = None
        template_id = None
        stage_env = {
            "PPTX_STAGE": STAGE_PREPARE,
            "PPTX_PREPARE_PATH": str(prepare_path or ""),
            "PPTX_PREPARE_OUTPUT_DIR": str(output_dir.resolve()),
            "PPTX_JOBSPEC_PATH": str(jobspec_path.resolve()),
            "PPTX_MODE": mode.lower(),
            "PPTX_PAGE_LIMIT": str(page_limit) if page_limit is not None else "",
        }
        if mode.lower() == "static":
            template_id = extract_template_id_from_json_file(jobspec_path)
            if template_id:
                hook_manager = load_hooks_for_template_id(template_id)
                stage_env["PPTX_TEMPLATE_ID"] = template_id
        if hook_manager and template_id:
            executed, continue_default = hook_manager.run_stage_hook(
                STAGE_PREPARE,
                env=stage_env,
            )
            if executed:
                click.echo(
                    f"[hooks] prepare stage executed via external hook (template_id={template_id})"
                )
                if not continue_default:
                    return

        config = build_prepare_config(
            prepare_path=prepare_path,
            output_dir=output_dir,
            jobspec=jobspec,
            mode=mode,
            page_limit=page_limit,
            default_policy_path=default_policy_path,
            default_jobspec_path=default_jobspec_path,
            prompts_dirname=prompts_dirname,
            slide_inputs_filename=slide_inputs_filename,
        )
        try:
            result = run_prepare_command(config, dump_json=dump_json)
        except PrepareCommandError as exc:
            click.echo(str(exc), err=True)
            raise click.exceptions.Exit(code=exc.exit_code) from exc

        for message in result.messages:
            click.echo(message)

        click.echo(f"Prepare Card: {result.cards_path}")
        click.echo(f"Prepare Log: {result.log_path}")
        click.echo(f"Prepare AI Log: {result.ai_log_path}")
        click.echo(f"AI Generation Meta: {result.meta_path}")
        click.echo(f"Prepare Story Outline: {result.story_outline_path}")
        click.echo(f"Audit Log: {result.audit_path}")

        if hook_manager and template_id:
            stage_env_with_outputs = dict(stage_env)
            stage_env_with_outputs.update(
                {
                    "PPTX_PREPARE_CARD_PATH": str(result.cards_path.resolve()),
                    "PPTX_PREPARE_LOG_PATH": str(result.log_path.resolve()),
                    "PPTX_PREPARE_AI_LOG_PATH": str(result.ai_log_path.resolve()),
                    "PPTX_PREPARE_META_PATH": str(result.meta_path.resolve()),
                    "PPTX_PREPARE_STORY_OUTLINE_PATH": str(result.story_outline_path.resolve()),
                    "PPTX_PREPARE_AUDIT_PATH": str(result.audit_path.resolve()),
                }
            )
            blueprint_slides = _load_blueprint_slides_from_jobspec(jobspec_path)
            if blueprint_slides:
                prompts_dir = _resolve_prompts_dir_from_jobspec(jobspec_path)
                contexts = slide_contexts_from_blueprint(
                    blueprint_slides, prompts_dir=prompts_dir
                )
                if contexts:
                    hook_manager.run_slide_hooks(
                        STAGE_PREPARE,
                        slides=contexts,
                        env=stage_env_with_outputs,
                    )

    return prepare


def _load_blueprint_slides_from_jobspec(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return []
    tpl_spec_rel = meta.get("template_spec_path")
    if not isinstance(tpl_spec_rel, str) or not tpl_spec_rel.strip():
        return []
    tpl_spec_path = (path.parent / tpl_spec_rel).resolve()
    try:
        tpl_payload = json.loads(tpl_spec_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    blueprint = tpl_payload.get("blueprint")
    if not isinstance(blueprint, dict):
        return []
    slides = blueprint.get("slides")
    if isinstance(slides, list):
        normalized: list[dict[str, Any]] = []
        for slide in slides:
            if isinstance(slide, dict):
                normalized.append(slide)
        return normalized
    return []


def _resolve_prompts_dir_from_jobspec(path: Path) -> Path | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return None
    template_spec_path = meta.get("template_spec_path")
    if not isinstance(template_spec_path, str) or not template_spec_path.strip():
        return None
    spec_dir = (path.parent / template_spec_path).resolve().parent
    prompts_dir = spec_dir / "prompts"
    if prompts_dir.exists():
        return prompts_dir
    return None


__all__ = [
    "build_prepare_config",
    "create_prepare_command",
]
