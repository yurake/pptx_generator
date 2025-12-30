from __future__ import annotations

from pathlib import Path

import click

from pptx_generator.cli_handlers.mapping import (
    MappingCommandConfig,
    MappingCommandError,
    echo_mapping_outputs,
    run_mapping_command,
)
from pptx_generator.cli_hooks import (
    STAGE_MAPPING,
    slide_contexts_from_generate_ready,
)
from pptx_generator.cli_commands.hook_runner import (
    load_stage_hooks,
    run_post_stage_slide_hooks,
    run_slide_hooks,
    run_stage_hook,
)
from .utils import handle_command_error


def create_mapping_command(
    *,
    default_output_dir: Path,
    default_rules_path: Path,
    default_prepare_cards_path: Path,
) -> click.Command:
    @click.command("mapping")
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
    def mapping(  # noqa: PLR0913
        spec_path: Path,
        output_dir: Path,
        rules: Path,
        prepare_cards: Path,
    ) -> None:
        """stage 5 マッピングを実行し generate_ready.json を生成する。"""

        draft_output = output_dir / "draft"
        hook_manager, template_id = load_stage_hooks(spec_path)
        stage_env = {
            "PPTX_STAGE": STAGE_MAPPING,
            "PPTX_SPEC_PATH": str(spec_path.resolve()),
            "PPTX_OUTPUT_DIR": str(output_dir.resolve()),
            "PPTX_RULES_PATH": str(rules.resolve()),
            "PPTX_DRAFT_OUTPUT": str(draft_output.resolve()),
            "PPTX_PREPARE_CARDS_PATH": str(prepare_cards.resolve()),
        }
        if template_id:
            stage_env["PPTX_TEMPLATE_ID"] = template_id
        if run_stage_hook(
            STAGE_MAPPING,
            hook_manager=hook_manager,
            template_id=template_id,
            stage_env=stage_env,
        ):
            return

        contexts = slide_contexts_from_generate_ready(prepare_cards)
        if run_slide_hooks(
            STAGE_MAPPING,
            hook_manager=hook_manager,
            stage_env=stage_env,
            slides=contexts,
            continue_default_filter=False,
        ):
            return

        config = MappingCommandConfig(
            spec_path=spec_path,
            output_dir=output_dir,
            rules_path=rules,
            draft_output=draft_output,
            prepare_cards=prepare_cards,
        )

        try:
            result = run_mapping_command(config)
        except MappingCommandError as exc:
            handle_command_error(exc, default_message="エラーが発生しました")
            raise click.exceptions.Exit(code=exc.exit_code) from exc

        echo_mapping_outputs(result.context)

        run_post_stage_slide_hooks(
            STAGE_MAPPING,
            hook_manager=hook_manager,
            template_id=template_id,
            base_stage_env=stage_env,
            generate_ready_path=output_dir / config.generate_ready_filename,
            slide_context_loader=slide_contexts_from_generate_ready,
        )

    return mapping


__all__ = ["create_mapping_command"]
