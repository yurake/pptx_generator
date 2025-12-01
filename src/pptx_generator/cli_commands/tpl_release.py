from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from pptx_generator.cli_handlers.template_commands import (
    TemplateCommandError,
    TemplateReleaseCommandConfig,
    run_template_release_command,
)
from pptx_generator.cli_handlers.template_release import echo_template_release_result


def create_tpl_release_command(
    *,
    default_output_dir: Path,
    default_layout_mode: str,
) -> click.Command:
    @click.command("tpl-release")
    @click.option(
        "--template",
        "-t",
        "template_path",
        type=click.Path(dir_okay=False, readable=True, path_type=Path),
        required=True,
        help="リリース対象の PPTX テンプレートファイル",
    )
    @click.option("--brand", type=str, required=True, help="ブランド名")
    @click.option("--version", type=str, required=True, help="テンプレートバージョン")
    @click.option(
        "--template-id",
        type=str,
        default=None,
        help="テンプレート識別子（未指定時は brand_version を使用）",
    )
    @click.option(
        "--output",
        "-o",
        "output_dir",
        type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
        default=default_output_dir,
        show_default=True,
        help="リリース成果物を保存するディレクトリ",
    )
    @click.option(
        "--generated-by",
        type=str,
        default=None,
        help="リリースメタの生成者",
    )
    @click.option(
        "--reviewed-by",
        type=str,
        default=None,
        help="レビュー担当者",
    )
    @click.option(
        "--baseline-release",
        type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
        default=None,
        help="比較対象となる過去の template_release.json",
    )
    @click.option(
        "--golden-spec",
        "golden_specs",
        type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
        multiple=True,
        help="テンプレ互換性検証に使用する spec ファイル（複数指定可）",
    )
    @click.option(
        "--layout-mode",
        type=click.Choice(["dynamic", "static"], case_sensitive=False),
        default=default_layout_mode,
        show_default=True,
        help="テンプレートの想定運用モード。static を指定すると Blueprint を出力する",
    )
    def tpl_release(
        template_path: Path,
        brand: str,
        version: str,
        template_id: Optional[str],
        output_dir: Path,
        generated_by: Optional[str],
        reviewed_by: Optional[str],
        baseline_release: Optional[Path],
        golden_specs: tuple[Path, ...],
        layout_mode: str,
    ) -> None:
        """テンプレート受け渡しメタと差分レポートを生成する。"""

        config = TemplateReleaseCommandConfig(
            template_path=template_path,
            brand=brand,
            version=version,
            template_id=template_id,
            output_dir=output_dir,
            generated_by=generated_by,
            reviewed_by=reviewed_by,
            baseline_release=baseline_release,
            golden_specs=golden_specs,
            layout_mode=layout_mode,
        )
        try:
            result = run_template_release_command(config)
        except TemplateCommandError as exc:
            message = str(exc)
            if message:
                click.echo(message, err=True)
            raise click.exceptions.Exit(code=exc.exit_code) from exc

        echo_template_release_result(result)

    return tpl_release


__all__ = ["create_tpl_release_command"]
