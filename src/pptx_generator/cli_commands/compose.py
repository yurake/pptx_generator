from __future__ import annotations

from pathlib import Path

import click

from pptx_generator.cli_handlers.compose import (
    ComposeCommandConfig,
    ComposeCommandError,
    run_compose_command,
)
from pptx_generator.runtime.job_queue import run_job_sync
from pptx_generator.cli_hooks import (
    STAGE_COMPOSE,
    slide_contexts_from_generate_ready,
)
from pptx_generator.cli_commands.hook_runner import (
    load_stage_hooks,
    run_post_stage_slide_hooks,
    run_slide_hooks,
    run_stage_hook,
)

from .utils import draft_common_options, handle_command_error


def _build_stage_env(
    *,
    spec_path: Path,
    output_dir: Path,
    draft_output: Path,
    target_length: int | None,
    structure_pattern: str | None,
    appendix_limit: int,
    analysis_summary_path: Path | None,
    show_layout_reasons: bool,
    rules: Path,
    prepare_cards: Path,
    template_id: str | None,
) -> dict[str, str]:
    chapter_templates_dir: Path | None = None
    chapter_template: str | None = structure_pattern
    stage_env = {
        "PPTX_STAGE": STAGE_COMPOSE,
        "PPTX_SPEC_PATH": str(spec_path.resolve()),
        "PPTX_OUTPUT_DIR": str(output_dir.resolve()),
        "PPTX_DRAFT_OUTPUT": str(draft_output.resolve()),
        "PPTX_TARGET_LENGTH": str(target_length) if target_length is not None else "",
        "PPTX_STRUCTURE_PATTERN": structure_pattern or "",
        "PPTX_APPENDIX_LIMIT": str(appendix_limit),
        "PPTX_ANALYSIS_SUMMARY_PATH": str(analysis_summary_path.resolve())
        if analysis_summary_path
        else "",
        "PPTX_SHOW_LAYOUT_REASONS": "1" if show_layout_reasons else "0",
        "PPTX_RULES_PATH": str(rules.resolve()),
        "PPTX_PREPARE_CARDS_PATH": str(prepare_cards.resolve()),
    }
    stage_env["PPTX_CHAPTER_TEMPLATES_DIR"] = (
        str(chapter_templates_dir.resolve()) if chapter_templates_dir else ""
    )
    stage_env["PPTX_CHAPTER_TEMPLATE"] = chapter_template or ""
    if template_id:
        stage_env["PPTX_TEMPLATE_ID"] = template_id
    return stage_env


def _run_stage_and_slide_hooks(
    *,
    hook_manager,
    template_id: str | None,
    stage_env: dict[str, str],
    prepare_cards: Path,
):
    if run_stage_hook(
        STAGE_COMPOSE,
        hook_manager=hook_manager,
        template_id=template_id,
        stage_env=stage_env,
    ):
        return None

    contexts = slide_contexts_from_generate_ready(prepare_cards)
    if run_slide_hooks(
        STAGE_COMPOSE,
        hook_manager=hook_manager,
        stage_env=stage_env,
        slides=contexts,
        continue_default_filter=False,
    ):
        return None
    return contexts


def _build_compose_config(
    *,
    spec_path: Path,
    draft_output: Path,
    target_length: int | None,
    structure_pattern: str | None,
    appendix_limit: int,
    analysis_summary_path: Path | None,
    show_layout_reasons: bool,
    output_dir: Path,
    rules: Path,
    prepare_cards: Path,
    slide_alignment: bool,
    slide_alignment_threshold: float | None,
    slide_alignment_max_candidates: int | None,
    default_draft_filename: str,
    default_approved_filename: str,
    default_draft_log_filename: str,
    default_draft_meta_filename: str,
    default_generate_ready_filename: str,
    default_generate_ready_meta_filename: str,
) -> ComposeCommandConfig:
    return ComposeCommandConfig(
        spec_path=spec_path,
        draft_output=draft_output,
        target_length=target_length,
        structure_pattern=structure_pattern,
        appendix_limit=appendix_limit,
        analysis_summary_path=analysis_summary_path,
        show_layout_reasons=show_layout_reasons,
        output_dir=output_dir,
        rules_path=rules,
        prepare_cards=prepare_cards,
        slide_alignment=slide_alignment,
        slide_alignment_threshold=slide_alignment_threshold,
        slide_alignment_max_candidates=slide_alignment_max_candidates,
        draft_filename=default_draft_filename,
        approved_filename=default_approved_filename,
        log_filename=default_draft_log_filename,
        meta_filename=default_draft_meta_filename,
        generate_ready_filename=default_generate_ready_filename,
        generate_ready_meta_filename=default_generate_ready_meta_filename,
    )


def _execute_compose(config: ComposeCommandConfig) -> None:
    try:
        run_job_sync(
            stage="compose",
            func=lambda: run_compose_command(config),
        )
    except ComposeCommandError as exc:
        handle_command_error(exc, default_message="エラーが発生しました")
        raise click.exceptions.Exit(code=exc.exit_code) from exc


def create_compose_command(
    *,
    default_appendix_limit: int,
    default_output_dir: Path,
    default_rules_path: Path,
    default_prepare_cards_path: Path,
    default_draft_filename: str,
    default_approved_filename: str,
    default_draft_log_filename: str,
    default_draft_meta_filename: str,
    default_generate_ready_filename: str,
    default_generate_ready_meta_filename: str,
) -> click.Command:
    @click.command("compose")
    @click.argument(
        "spec_path",
        type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    )
    @draft_common_options(
        default_appendix_limit=default_appendix_limit,
        default_prepare_cards_path=default_prepare_cards_path,
        prepare_cards_exists=True,
    )
    @click.option(
        "--output",
        "-o",
        "output_dir",
        type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
        default=default_output_dir,
        show_default=True,
        help="generate_ready.json 等の出力ディレクトリ",
    )
    @click.option(
        "--rules",
        type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
        default=default_rules_path,
        show_default=True,
        help="検証ルール設定ファイル",
    )
    def compose(  # noqa: PLR0913
        spec_path: Path,
        target_length: int | None,
        structure_pattern: str | None,
        appendix_limit: int,
        analysis_summary_path: Path | None,
        show_layout_reasons: bool,
        output_dir: Path,
        rules: Path,
        prepare_cards: Path,
        slide_alignment: bool,
        slide_alignment_threshold: float | None,
        slide_alignment_max_candidates: int | None,
    ) -> None:
        """stage 4+5 を連続実行しドラフトとマッピング成果物を生成する。"""

        draft_output = output_dir / "draft"
        hook_manager, template_id = load_stage_hooks(spec_path)
        stage_env = _build_stage_env(
            spec_path=spec_path,
            output_dir=output_dir,
            draft_output=draft_output,
            target_length=target_length,
            structure_pattern=structure_pattern,
            appendix_limit=appendix_limit,
            analysis_summary_path=analysis_summary_path,
            show_layout_reasons=show_layout_reasons,
            rules=rules,
            prepare_cards=prepare_cards,
            template_id=template_id,
        )

        contexts = _run_stage_and_slide_hooks(
            hook_manager=hook_manager,
            template_id=template_id,
            stage_env=stage_env,
            prepare_cards=prepare_cards,
        )
        if contexts is None:
            return

        config = _build_compose_config(
            spec_path=spec_path,
            draft_output=draft_output,
            target_length=target_length,
            structure_pattern=structure_pattern,
            appendix_limit=appendix_limit,
            analysis_summary_path=analysis_summary_path,
            show_layout_reasons=show_layout_reasons,
            output_dir=output_dir,
            rules=rules,
            prepare_cards=prepare_cards,
            slide_alignment=slide_alignment,
            slide_alignment_threshold=slide_alignment_threshold,
            slide_alignment_max_candidates=slide_alignment_max_candidates,
            default_draft_filename=default_draft_filename,
            default_approved_filename=default_approved_filename,
            default_draft_log_filename=default_draft_log_filename,
            default_draft_meta_filename=default_draft_meta_filename,
            default_generate_ready_filename=default_generate_ready_filename,
            default_generate_ready_meta_filename=default_generate_ready_meta_filename,
        )

        _execute_compose(config)

        run_post_stage_slide_hooks(
            STAGE_COMPOSE,
            hook_manager=hook_manager,
            template_id=template_id,
            base_stage_env=stage_env,
            generate_ready_path=output_dir / default_generate_ready_filename,
            slide_context_loader=slide_contexts_from_generate_ready,
        )

    return compose


__all__ = ["create_compose_command"]
