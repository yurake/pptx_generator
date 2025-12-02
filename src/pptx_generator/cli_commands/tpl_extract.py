from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from pptx_generator.cli_handlers.template_commands import (
    TemplateCommandError,
    TemplateExtractCommandConfig,
    run_template_extract_command,
)


def create_tpl_extract_command(
    *,
    default_output_dir: Path,
    default_layout_mode: str,
) -> click.Command:
    @click.command("tpl-extract")
    @click.option(
        "--template",
        "-t",
        "template_path",
        type=click.Path(dir_okay=False, readable=True, path_type=Path),
        required=True,
        help="抽出対象の PPTX テンプレートファイル",
    )
    @click.option(
        "--layout",
        type=str,
        default=None,
        help="抽出対象レイアウト名のフィルタ（前方一致）",
    )
    @click.option(
        "--anchor",
        type=str,
        default=None,
        help="抽出対象アンカー名のフィルタ（前方一致）",
    )
    @click.option(
        "--format",
        type=click.Choice(["json", "yaml"], case_sensitive=False),
        default="json",
        show_default=True,
        help="出力形式",
    )
    @click.option(
        "--layout-mode",
        type=click.Choice(["dynamic", "static"], case_sensitive=False),
        default=default_layout_mode,
        show_default=True,
        help="テンプレートの想定運用モード。static を指定すると Blueprint を出力する",
    )
    @click.option(
        "--output",
        "-o",
        "output_dir",
        type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
        default=default_output_dir,
        show_default=True,
        help="テンプレート仕様とブランド設定を保存するディレクトリ",
    )
    @click.option(
        "--template-ai-policy",
        type=click.Path(dir_okay=False, readable=True, path_type=Path),
        default=None,
        help="テンプレート usage_tags 推定に使用する AI ポリシー JSON",
    )
    @click.option(
        "--template-ai-policy-id",
        type=str,
        default=None,
        help="テンプレート AI ポリシーセット内の利用対象 ID",
    )
    @click.option(
        "--disable-template-ai",
        is_flag=True,
        default=False,
        help="生成AIによる usage_tags 推定を無効化する",
    )
    def tpl_extract(
        template_path: Path,
        output_dir: Path,
        layout: Optional[str],
        anchor: Optional[str],
        format: str,
        layout_mode: str,
        template_ai_policy: Path | None,
        template_ai_policy_id: str | None,
        disable_template_ai: bool,
    ) -> None:
        """テンプレートファイルから図形・プレースホルダー情報を抽出してJSON仕様の雛形を生成する。"""
        config = TemplateExtractCommandConfig(
            template_path=template_path,
            output_dir=output_dir,
            format=format,
            layout=layout,
            anchor=anchor,
            layout_mode=layout_mode,
            template_ai_policy=template_ai_policy,
            template_ai_policy_id=template_ai_policy_id,
            disable_template_ai=disable_template_ai,
        )

        try:
            run_template_extract_command(config)
        except TemplateCommandError as exc:
            message = str(exc)
            if message:
                click.echo(message, err=True)
            raise click.exceptions.Exit(code=exc.exit_code) from exc

    return tpl_extract


__all__ = ["create_tpl_extract_command"]
