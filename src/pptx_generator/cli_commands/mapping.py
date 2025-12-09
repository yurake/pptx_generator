from __future__ import annotations

from pathlib import Path

import click

from pptx_generator.cli_handlers.mapping import (
    MappingCommandConfig,
    MappingCommandError,
    echo_mapping_outputs,
    run_mapping_command,
)

from .utils import echo_command_errors
from pptx_generator.cli_hooks import (
    STAGE_MAPPING,
    slide_contexts_from_generate_ready,
    extract_template_id_from_json_file,
    load_hooks_for_template_id,
)


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
        hook_manager = None
        template_id = extract_template_id_from_json_file(spec_path)
        if template_id:
            hook_manager = load_hooks_for_template_id(template_id)
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
        if hook_manager:
            executed, continue_default = hook_manager.run_stage_hook(
                STAGE_MAPPING,
                env=stage_env,
            )
            if executed:
                click.echo(
                    f"[hooks] mapping stage executed via external hook (template_id={template_id})"
                )
                if not continue_default:
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
            message = str(exc)
            if exc.errors:
                echo_command_errors(message or "エラーが発生しました", exc.errors)
            elif message:
                click.echo(message, err=True)
            raise click.exceptions.Exit(code=exc.exit_code) from exc

        echo_mapping_outputs(result.context)

        if hook_manager and template_id:
            stage_env_with_outputs = dict(stage_env)
            generate_ready_path = output_dir / config.generate_ready_filename
            stage_env_with_outputs["PPTX_GENERATE_READY_PATH"] = str(generate_ready_path.resolve())
            contexts = slide_contexts_from_generate_ready(generate_ready_path)
            if contexts:
                hook_manager.run_slide_hooks(
                    STAGE_MAPPING,
                    slides=contexts,
                    env=stage_env_with_outputs,
                )

    return mapping


__all__ = ["create_mapping_command"]
