from __future__ import annotations

from pathlib import Path

import click

from pptx_generator.cli_handlers.compose import (
    ComposeCommandConfig,
    ComposeCommandError,
    run_compose_command,
)

from .utils import echo_command_errors
from pptx_generator.cli_hooks import (
    STAGE_COMPOSE,
    slide_contexts_from_generate_ready,
    extract_template_id_from_json_file,
    load_hooks_for_template_id,
)


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
        "--import-analysis",
        "analysis_summary_path",
        type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
        default=None,
        help="analysis_summary.json のパス",
    )
    @click.option(
        "--show-layout-reasons",
        is_flag=True,
        default=False,
        help="layout_hint 候補のスコア内訳を表示する",
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
    @click.option(
        "--prepare-cards",
        type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
        default=default_prepare_cards_path,
        show_default=True,
        help="stage 2 の prepare_card.json",
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
        hook_manager = None
        template_id = extract_template_id_from_json_file(spec_path)
        if template_id:
            hook_manager = load_hooks_for_template_id(template_id)
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
        if hook_manager:
            executed, continue_default = hook_manager.run_stage_hook(
                STAGE_COMPOSE,
                env=stage_env,
            )
            if executed:
                click.echo(
                    f"[hooks] compose stage executed via external hook (template_id={template_id})"
                )
                if not continue_default:
                    return

        contexts = slide_contexts_from_generate_ready(prepare_cards)
        if hook_manager:
            executed = hook_manager.run_slide_hooks(
                STAGE_COMPOSE,
                slides=contexts,
                env=stage_env,
                continue_default_filter=False,
                allow_fallback_context=True,
            )
            if executed:
                return

        config = ComposeCommandConfig(
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
        try:
            run_compose_command(config)
        except ComposeCommandError as exc:
            message = str(exc)
            if exc.errors:
                echo_command_errors(message or "エラーが発生しました", exc.errors)
            elif message:
                click.echo(message, err=True)
            raise click.exceptions.Exit(code=exc.exit_code) from exc

        if hook_manager and template_id:
            stage_env_with_outputs = dict(stage_env)
            generate_ready_path = output_dir / default_generate_ready_filename
            stage_env_with_outputs["PPTX_GENERATE_READY_PATH"] = str(generate_ready_path.resolve())
            contexts = slide_contexts_from_generate_ready(generate_ready_path)
            hook_manager.run_slide_hooks(
                STAGE_COMPOSE,
                slides=contexts,
                env=stage_env_with_outputs,
                continue_default_filter=True,
                allow_fallback_context=True,
            )

    return compose


__all__ = ["create_compose_command"]
