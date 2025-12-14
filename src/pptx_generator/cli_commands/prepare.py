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
    extract_template_id_from_json_file,
    load_hooks_for_template_id,
    slide_contexts_from_blueprint,
)


def build_prepare_config(
    *,
    prepare_path: Path | None,
    prepare_inputs: tuple[str, ...],
    output_dir: Path,
    jobspec: Path | None,
    mode: str,
    page_limit: int | None,
    default_jobspec_path: Path,
    prompts_dirname: Path,
    slide_inputs_filename: Path,
) -> PrepareCommandConfig:
    return PrepareCommandConfig(
        prepare_path=prepare_path,
        prepare_inputs=prepare_inputs,
        output_dir=output_dir,
        jobspec_path=jobspec,
        mode=mode,
        page_limit=page_limit,
        default_jobspec_path=default_jobspec_path,
        prompts_dirname=prompts_dirname,
        slide_inputs_filename=slide_inputs_filename,
    )


def create_prepare_command(
    *,
    default_output_dir: Path,
    default_jobspec_path: Path,
    prompts_dirname: Path,
    slide_inputs_filename: Path = SLIDE_INPUTS_FILENAME,
) -> click.Command:
    @click.command("prepare")
    @click.argument(
        "prepare_inputs",
        nargs=-1,
        type=str,
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
        type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
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
        prepare_inputs: tuple[str, ...],
        output_dir: Path,
        jobspec: Path | None,
        mode: str,
        page_limit: int | None,
    ) -> None:
        """stage 2 コンテンツ準備: PrepareCard 成果物を生成する。"""

        normalized_inputs: list[str] = []
        for raw in prepare_inputs:
            parts = [item.strip() for item in raw.split(",") if item.strip()]
            if parts:
                normalized_inputs.extend(parts)

        primary_prepare_path: Path | None = None
        for candidate in normalized_inputs:
            candidate_path = Path(candidate).expanduser()
            if candidate_path.exists() and candidate_path.is_file():
                primary_prepare_path = candidate_path
                break

        jobspec_path = jobspec or default_jobspec_path
        hook_manager = None
        template_id = None
        stage_env = {
            "PPTX_STAGE": STAGE_PREPARE,
            "PPTX_PREPARE_PATH": str(primary_prepare_path or ""),
            "PPTX_PREPARE_INPUTS": "\n".join(normalized_inputs),
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
            prepare_path=primary_prepare_path,
            prepare_inputs=tuple(normalized_inputs),
            output_dir=output_dir,
            jobspec=jobspec,
            mode=mode,
            page_limit=page_limit,
            default_jobspec_path=default_jobspec_path,
            prompts_dirname=prompts_dirname,
            slide_inputs_filename=slide_inputs_filename,
        )

        contexts: list[dict[str, Any]] = []
        if hook_manager and template_id:
            blueprint_slides = _load_blueprint_slides_from_jobspec(jobspec_path)
            prompts_dir = _resolve_prompts_dir_from_jobspec(jobspec_path)
            contexts = (
                slide_contexts_from_blueprint(
                    blueprint_slides,
                    prompts_dir=prompts_dir,
                )
                if blueprint_slides
                else []
            )
            executed = hook_manager.run_slide_hooks(
                STAGE_PREPARE,
                slides=contexts,
                env=stage_env,
                continue_default_filter=False,
                allow_fallback_context=True,
            )
            if executed:
                return

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
            hook_manager.run_slide_hooks(
                STAGE_PREPARE,
                slides=contexts,
                env=stage_env_with_outputs,
                continue_default_filter=True,
                allow_fallback_context=True,
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
