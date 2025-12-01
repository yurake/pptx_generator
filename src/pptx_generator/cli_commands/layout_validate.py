from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from pptx_generator.cli_handlers.layout_validation import (
    LayoutValidateCommandConfig,
    LayoutValidateCommandError,
    echo_layout_validation_result,
    run_layout_validate_command,
)


def create_layout_validate_command(
    *,
    default_output_dir: Path,
) -> click.Command:
    @click.command("layout-validate")
    @click.option(
        "--template",
        "-t",
        "template_path",
        type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
        required=True,
        help="検証対象の PPTX テンプレートファイル",
    )
    @click.option(
        "--output",
        "-o",
        "output_dir",
        type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
        default=default_output_dir,
        show_default=True,
        help="検証成果物の出力ディレクトリ",
    )
    @click.option(
        "--template-id",
        type=str,
        default=None,
        help="layouts.jsonl に記録するテンプレート ID",
    )
    @click.option(
        "--baseline",
        type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
        default=None,
        help="比較対象となる過去の layouts.jsonl",
    )
    @click.option(
        "--analyzer-snapshot",
        type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
        default=None,
        help="Analyzer が出力した構造スナップショット JSON",
    )
    def layout_validate(
        template_path: Path,
        output_dir: Path,
        template_id: Optional[str],
        baseline: Optional[Path],
        analyzer_snapshot: Optional[Path],
    ) -> None:
        """テンプレート構造の検証スイートを実行する。"""

        config = LayoutValidateCommandConfig(
            template_path=template_path,
            output_dir=output_dir,
            template_id=template_id,
            baseline=baseline,
            analyzer_snapshot=analyzer_snapshot,
        )

        try:
            result = run_layout_validate_command(config)
        except LayoutValidateCommandError as exc:
            message = str(exc)
            if message:
                click.echo(message, err=True)
            raise click.exceptions.Exit(code=exc.exit_code) from exc

        echo_layout_validation_result(result)

    return layout_validate


__all__ = ["create_layout_validate_command"]
