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


def create_mapping_command(
    *,
    default_output_dir: Path,
    default_rules_path: Path,
    default_draft_output: Path,
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
        "--draft-output",
        type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
        default=default_draft_output,
        show_default=True,
        help="draft_draft.json / draft_approved.json の出力先",
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
        draft_output: Path,
        prepare_cards: Path,
    ) -> None:
        """stage 5 マッピングを実行し generate_ready.json を生成する。"""
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

    return mapping


__all__ = ["create_mapping_command"]
