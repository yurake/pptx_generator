from __future__ import annotations

from pathlib import Path

import click

from pptx_generator.cli_handlers.outline import (
    OutlineCommandConfig,
    run_outline_command,
)
from pptx_generator.pipeline import PrepareNormalizationError
from pptx_generator.pipeline.draft_structuring import DraftStructuringError

from .utils import draft_common_options


def create_outline_command(
    *,
    default_output_dir: Path,
    default_appendix_limit: int,
    default_prepare_cards_path: Path,
    default_draft_filename: str,
    default_approved_filename: str,
    default_draft_log_filename: str,
    default_generate_ready_filename: str,
    default_generate_ready_meta_filename: str,
    default_draft_meta_filename: str,
) -> click.Command:
    @click.command("outline")
    @click.argument(
        "spec_path",
        type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    )
    @click.option(
        "--output",
        "-o",
        "output_dir",
        type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
        default=default_output_dir,
        show_default=True,
        help="ドラフト成果物を保存するディレクトリ",
    )
    @draft_common_options(
        default_appendix_limit=default_appendix_limit,
        default_prepare_cards_path=default_prepare_cards_path,
        prepare_cards_exists=False,
    )
    def outline(
        spec_path: Path,
        output_dir: Path,
        target_length: int | None,
        structure_pattern: str | None,
        appendix_limit: int,
        analysis_summary_path: Path | None,
        show_layout_reasons: bool,
        prepare_cards: Path,
        slide_alignment: bool,
        slide_alignment_threshold: float | None,
        slide_alignment_max_candidates: int | None,
    ) -> None:
        """stage 4 ドラフト構成（アウトライン）を生成する。"""

        config = OutlineCommandConfig(
            spec_path=spec_path,
            output_dir=output_dir,
            target_length=target_length,
            structure_pattern=structure_pattern,
            appendix_limit=appendix_limit,
            analysis_summary_path=analysis_summary_path,
            prepare_cards=prepare_cards,
            require_prepare=True,
            show_layout_reasons=show_layout_reasons,
            slide_alignment=slide_alignment,
            slide_alignment_threshold=slide_alignment_threshold,
            slide_alignment_max_candidates=slide_alignment_max_candidates,
            draft_filename=default_draft_filename,
            approved_filename=default_approved_filename,
            log_filename=default_draft_log_filename,
            generate_ready_filename=default_generate_ready_filename,
            generate_ready_meta_filename=default_generate_ready_meta_filename,
            meta_filename=default_draft_meta_filename,
        )

        try:
            run_outline_command(config)
        except PrepareNormalizationError as exc:
            click.echo(f"プレペア成果物の読み込みに失敗しました: {exc}", err=True)
            raise click.exceptions.Exit(code=4) from exc
        except DraftStructuringError as exc:
            click.echo(f"ドラフト構成の生成に失敗しました: {exc}", err=True)
            raise click.exceptions.Exit(code=4) from exc

    return outline


__all__ = ["create_outline_command"]
