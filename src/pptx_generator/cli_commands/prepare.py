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
from pptx_generator.runtime.job_queue import run_job_sync


def normalize_prepare_inputs(prepare_inputs: tuple[str, ...]) -> list[str]:
    normalized_inputs: list[str] = []
    for raw in prepare_inputs:
        parts = [item.strip() for item in raw.split(",") if item.strip()]
        if parts:
            normalized_inputs.extend(parts)
    return normalized_inputs


def determine_primary_prepare_path(normalized_inputs: list[str]) -> Path | None:
    for candidate in normalized_inputs:
        candidate_path = Path(candidate).expanduser()
        if candidate_path.exists() and candidate_path.is_file():
            return candidate_path
    return None


def build_stage_env(
    *,
    mode: str,
    primary_prepare_path: Path | None,
    normalized_inputs: list[str],
    output_dir: Path,
    jobspec_path: Path,
    page_limit: int | None,
) -> dict[str, str]:
    return {
        "PPTX_STAGE": STAGE_PREPARE,
        "PPTX_PREPARE_PATH": str(primary_prepare_path or ""),
        "PPTX_PREPARE_INPUTS": "\n".join(normalized_inputs),
        "PPTX_PREPARE_OUTPUT_DIR": str(output_dir.resolve()),
        "PPTX_JOBSPEC_PATH": str(jobspec_path.resolve()),
        "PPTX_MODE": mode,
        "PPTX_PAGE_LIMIT": str(page_limit) if page_limit is not None else "",
    }


def load_hook_manager_if_static(
    *, mode: str, jobspec_path: Path, stage_env: dict[str, str]
) -> tuple[Any | None, str | None]:
    template_id = None
    hook_manager = None
    if mode == "static":
        template_id = extract_template_id_from_json_file(jobspec_path)
        if template_id:
            hook_manager = load_hooks_for_template_id(template_id)
            stage_env["PPTX_TEMPLATE_ID"] = template_id
    return hook_manager, template_id


def run_stage_hook_if_needed(
    *, hook_manager: Any | None, template_id: str | None, stage_env: dict[str, str]
) -> bool:
    if not hook_manager or not template_id:
        return True

    executed, continue_default = hook_manager.run_stage_hook(
        STAGE_PREPARE,
        env=stage_env,
    )
    if executed:
        click.echo(
            f"[hooks] prepare stage executed via external hook (template_id={template_id})"
        )
        if not continue_default:
            return False
    return True


def run_pre_slide_hooks(
    *,
    hook_manager: Any | None,
    template_id: str | None,
    jobspec_path: Path,
    stage_env: dict[str, str],
) -> tuple[list[dict[str, Any]], bool]:
    contexts: list[dict[str, Any]] = []
    if not hook_manager or not template_id:
        return contexts, False

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
    if template_id and not contexts:
        click.echo("[hooks] no slide contexts resolved; continuing with default")
    executed = hook_manager.run_slide_hooks(
        STAGE_PREPARE,
        slides=contexts,
        env=stage_env,
        continue_default_filter=False,
        allow_fallback_context=True,
    )
    return contexts, executed


def execute_prepare_command(config: PrepareCommandConfig) -> Any:
    try:
        return run_job_sync(
            stage="prepare",
            func=lambda: run_prepare_command(config, dump_json=dump_json),
        )
    except PrepareCommandError as exc:
        click.echo(str(exc), err=True)
        raise click.exceptions.Exit(code=exc.exit_code) from exc


def echo_prepare_outputs(result: Any) -> None:
    for message in result.messages:
        click.echo(message)

    click.echo(f"Prepare Card: {result.cards_path}")
    click.echo(f"Prepare Log: {result.log_path}")
    click.echo(f"Prepare AI Log: {result.ai_log_path}")
    click.echo(f"AI Generation Meta: {result.meta_path}")
    click.echo(f"Prepare Story Outline: {result.story_outline_path}")
    click.echo(f"Audit Log: {result.audit_path}")


def run_post_slide_hooks(
    *,
    hook_manager: Any | None,
    template_id: str | None,
    stage_env: dict[str, str],
    contexts: list[dict[str, Any]],
    result: Any,
) -> None:
    if not hook_manager or not template_id:
        return

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
        type=click.Choice(["dynamic"], case_sensitive=False),
        required=True,
        help="カード生成モード。dynamic のみ利用可能",
    )
    @click.option(
        "--jobspec",
        type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
        default=None,
        help="静的モードで参照する jobspec.json (未指定時は .pptx/template/jobspec.json を探索)",
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

        normalized_inputs = normalize_prepare_inputs(prepare_inputs)
        primary_prepare_path = determine_primary_prepare_path(normalized_inputs)
        jobspec_path = jobspec or default_jobspec_path

        mode_normalized = mode.lower()
        stage_env = build_stage_env(
            mode=mode_normalized,
            primary_prepare_path=primary_prepare_path,
            normalized_inputs=normalized_inputs,
            output_dir=output_dir,
            jobspec_path=jobspec_path,
            page_limit=page_limit,
        )

        hook_manager, template_id = load_hook_manager_if_static(
            mode=mode_normalized,
            jobspec_path=jobspec_path,
            stage_env=stage_env,
        )
        if not run_stage_hook_if_needed(
            hook_manager=hook_manager,
            template_id=template_id,
            stage_env=stage_env,
        ):
            return

        config = build_prepare_config(
            prepare_path=primary_prepare_path,
            prepare_inputs=tuple(normalized_inputs),
            output_dir=output_dir,
            jobspec=jobspec,
            mode=mode_normalized,
            page_limit=page_limit,
            default_jobspec_path=default_jobspec_path,
            prompts_dirname=prompts_dirname,
            slide_inputs_filename=slide_inputs_filename,
        )

        contexts, executed = run_pre_slide_hooks(
            hook_manager=hook_manager,
            template_id=template_id,
            jobspec_path=jobspec_path,
            stage_env=stage_env,
        )
        if executed:
            return

        result = execute_prepare_command(config)

        echo_prepare_outputs(result)

        run_post_slide_hooks(
            hook_manager=hook_manager,
            template_id=template_id,
            stage_env=stage_env,
            contexts=contexts,
            result=result,
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
