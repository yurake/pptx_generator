from __future__ import annotations

from pathlib import Path

import click

from pptx_generator.cli_handlers.compose import (
    ComposeCommandConfig,
    ComposeCommandError,
    run_compose_command,
)
from pptx_generator.runtime.job_queue import run_job_sync
from pptx_generator.executive_board.common.script_runner import run_compose_scripts

from .utils import draft_common_options, handle_command_error


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
    ) -> None:
        """stage 4+5 を連続実行しドラフトとマッピング成果物を生成する。"""

        draft_output = output_dir / "draft"

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
            default_draft_filename=default_draft_filename,
            default_approved_filename=default_approved_filename,
            default_draft_log_filename=default_draft_log_filename,
            default_draft_meta_filename=default_draft_meta_filename,
            default_generate_ready_filename=default_generate_ready_filename,
            default_generate_ready_meta_filename=default_generate_ready_meta_filename,
        )

        _execute_compose(config)

        run_compose_scripts(
            generate_ready_path=output_dir / default_generate_ready_filename,
            output_dir=output_dir,
            context_path=None,
        )

    return compose


__all__ = ["create_compose_command"]
