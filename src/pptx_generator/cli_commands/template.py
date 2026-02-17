from __future__ import annotations

from pathlib import Path

import click

from pptx_generator.cli_handlers.template_commands import (
    TemplateCommandConfig,
    TemplateCommandError,
    run_template_command,
)
from pptx_generator.runtime.job_queue import run_job_sync

from pptx_generator.cli_handlers.common import log_current_llm_provider


def create_template_command(
    *,
    default_extract_output: Path,
    default_mode: str,
) -> click.Command:
    @click.command("template")
    @click.argument(
        "template_path",
        type=click.Path(dir_okay=False, readable=True, path_type=Path),
    )
    @click.option(
        "--output",
        "-o",
        type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
        default=default_extract_output,
        show_default=True,
        help="抽出・検証結果を保存するディレクトリ",
    )
    @click.option(
        "--format",
        type=click.Choice(["json", "yaml"], case_sensitive=False),
        default="json",
        show_default=True,
        help="テンプレート仕様の出力形式",
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
        "--mode",
        type=click.Choice(["dynamic", "static"], case_sensitive=False),
        default=default_mode,
        show_default=True,
        help="テンプレートの想定運用モード。static を指定すると Blueprint を出力する",
    )
    @click.option(
        "--from",
        "static_source",
        type=click.Choice(["slide", "template"]),
        default="slide",
        show_default=True,
        help="static モード時にテンプレ抽出へ使用するソースを指定する",
    )
    @click.option(
        "--slide",
        is_flag=True,
        default=False,
        help="実スライドの図形・段落情報を slide_snapshot.json として出力する",
    )
    @click.option(
        "--force",
        "-f",
        is_flag=True,
        default=False,
        help="レイアウト検証をスキップして強制的にテンプレ stage を継続する（緊急時のみ使用）",
    )
    def template(  # noqa: PLR0913
        template_path: Path,
        output: Path,
        format: str,
        layout: str | None,
        anchor: str | None,
        mode: str,
        static_source: str,
        slide: bool,
        force: bool,
    ) -> None:
        """テンプレ stage（抽出・検証・必要に応じてリリース）を実行する。"""

        log_current_llm_provider("template")

        config = TemplateCommandConfig(
            template_path=template_path,
            output_dir=output,
            format=format,
            layout=layout,
            anchor=anchor,
            layout_mode=mode,
            static_source=static_source,
            slide_snapshot=slide,
            force=force,
        )

        try:
            result = run_job_sync(
                stage="template",
                func=lambda: run_template_command(config),
            )
        except TemplateCommandError as exc:
            message = str(exc)
            if message:
                click.echo(message, err=True)
            raise click.exceptions.Exit(code=exc.exit_code) from exc

        extraction_result = result.extraction

        if extraction_result.prompt_templates_dir is not None:
            click.echo(f"プロンプト雛形を出力しました: {extraction_result.prompt_templates_dir}")
            if extraction_result.prompt_templates_created:
                click.echo(
                    f"  -> {extraction_result.prompt_templates_created} 件のスライド雛形を生成しました。必要に応じて編集し、prepare で反映してください。"
                )
            else:
                click.echo("  -> 既存の雛形を保持しました。変更があればファイルを手動で更新してください。")

        click.echo("テンプレ stage（抽出＋検証）が完了しました。")


    return template


__all__ = ["create_template_command"]
