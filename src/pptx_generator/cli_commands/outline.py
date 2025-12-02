from __future__ import annotations

from pathlib import Path

import click

from pptx_generator.cli_handlers.outline import (
    OutlineCommandConfig,
    run_outline_command,
)
from pptx_generator.pipeline import PrepareNormalizationError
from pptx_generator.pipeline.draft_structuring import DraftStructuringError


def create_outline_command(
    *,
    default_output_dir: Path,
    default_appendix_limit: int,
    default_chapter_templates_dir: Path,
    default_prepare_cards_path: Path,
    default_return_reasons_path: Path,
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
    @click.option(
        "--target-length",
        type=int,
        default=None,
        help="目標スライド枚数",
    )
    @click.option(
        "--structure-pattern",
        type=str,
        default=None,
        help="章構成パターン名",
    )
    @click.option(
        "--appendix-limit",
        type=int,
        default=default_appendix_limit,
        show_default=True,
        help="付録枚数の上限",
    )
    @click.option(
        "--chapter-templates-dir",
        type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
        default=default_chapter_templates_dir,
        show_default=True,
        help="章テンプレート辞書ディレクトリ",
    )
    @click.option(
        "--chapter-template",
        type=str,
        default=None,
        help="適用する章テンプレート ID",
    )
    @click.option(
        "--import-analysis",
        "analysis_summary_path",
        type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
        default=None,
        help="analysis_summary.json のパス",
    )
    @click.option(
        "--return-reasons-path",
        type=click.Path(dir_okay=False, writable=False, path_type=Path),
        default=default_return_reasons_path,
        show_default=True,
        help="差戻し理由テンプレート辞書のパス",
    )
    @click.option(
        "--return-reasons",
        is_flag=True,
        default=False,
        help="差戻し理由テンプレート一覧を表示して終了する",
    )
    @click.option(
        "--show-layout-reasons",
        is_flag=True,
        default=False,
        help="layout_hint 候補のスコア内訳を表示する",
    )
    @click.option(
        "--prepare-cards",
        type=click.Path(exists=False, dir_okay=False, readable=True, path_type=Path),
        default=default_prepare_cards_path,
        show_default=True,
        help="stage 2 の prepare_card.json",
    )
    def outline(
        spec_path: Path,
        output_dir: Path,
        target_length: int | None,
        structure_pattern: str | None,
        appendix_limit: int,
        chapter_templates_dir: Path,
        chapter_template: str | None,
        analysis_summary_path: Path | None,
        return_reasons_path: Path,
        return_reasons: bool,
        show_layout_reasons: bool,
        prepare_cards: Path,
    ) -> None:
        """stage 4 ドラフト構成（アウトライン）を生成する。"""

        config = OutlineCommandConfig(
            spec_path=spec_path,
            output_dir=output_dir,
            target_length=target_length,
            structure_pattern=structure_pattern,
            appendix_limit=appendix_limit,
            chapter_templates_dir=chapter_templates_dir,
            chapter_template=chapter_template,
            analysis_summary_path=analysis_summary_path,
            prepare_cards=prepare_cards,
            require_prepare=True,
            return_reasons_path=return_reasons_path,
            return_reasons=return_reasons,
            show_layout_reasons=show_layout_reasons,
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
