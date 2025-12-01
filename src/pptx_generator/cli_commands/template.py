from __future__ import annotations

from pathlib import Path

import click

from pptx_generator.cli_handlers.template_commands import (
    TemplateCommandConfig,
    TemplateCommandError,
    run_template_command,
)

from pptx_generator.cli_handlers.common import log_current_llm_provider


def create_template_command(
    *,
    default_extract_output: Path,
    default_release_output: Path,
    default_layout_mode: str,
    default_template_ai_policy: Path | None = None,
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
        "--layout-mode",
        type=click.Choice(["dynamic", "static"], case_sensitive=False),
        default=default_layout_mode,
        show_default=True,
        help="テンプレートの想定運用モード。static を指定すると Blueprint を出力する",
    )
    @click.option(
        "--with-release",
        is_flag=True,
        help="抽出・検証後にテンプレートリリースメタも生成する",
    )
    @click.option("--brand", type=str, default=None, help="--with-release 時のブランド名")
    @click.option("--version", type=str, default=None, help="--with-release 時のテンプレートバージョン")
    @click.option(
        "--template-id",
        type=str,
        default=None,
        help="--with-release 時のテンプレート識別子。未指定時は <brand>_<version> を使用",
    )
    @click.option(
        "--release-output",
        type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
        default=default_release_output,
        show_default=True,
        help="テンプレートリリース成果物の出力ディレクトリ",
    )
    @click.option("--generated-by", type=str, default=None, help="テンプレートリリースメタの生成者")
    @click.option("--reviewed-by", type=str, default=None, help="テンプレートリリースメタのレビュー担当者")
    @click.option(
        "--baseline-release",
        type=click.Path(exists=True, dir_okay=False,
                        readable=True, path_type=Path),
        default=None,
        help="比較対象となる過去の template_release.json",
    )
    @click.option(
        "--golden-spec",
        "golden_specs",
        type=click.Path(exists=True, dir_okay=False,
                        readable=True, path_type=Path),
        multiple=True,
        help="テンプレ互換性検証に使用する spec ファイル（複数指定可）",
    )
    @click.option(
        "--template-ai-policy",
        type=click.Path(dir_okay=False, readable=True, path_type=Path),
        default=default_template_ai_policy,
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
        layout_mode: str,
        with_release: bool,
        brand: str | None,
        version: str | None,
        template_id: str | None,
        release_output: Path,
        generated_by: str | None,
        reviewed_by: str | None,
        baseline_release: Path | None,
        golden_specs: tuple[Path, ...],
        template_ai_policy: Path | None,
        template_ai_policy_id: str | None,
        disable_template_ai: bool,
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
            layout_mode=layout_mode,
            template_ai_policy=template_ai_policy,
            template_ai_policy_id=template_ai_policy_id,
            disable_template_ai=disable_template_ai,
            with_release=with_release,
            brand=brand,
            version=version,
            template_id=template_id,
            release_output=release_output,
            generated_by=generated_by,
            reviewed_by=reviewed_by,
            baseline_release=baseline_release,
            golden_specs=golden_specs,
            slide_snapshot=slide,
            force=force,
        )

        try:
            result = run_template_command(config)
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
                    f"  -> {extraction_result.prompt_templates_created} 件のスライド雛形を生成しました。必要に応じて編集し、static prepare で反映してください。"
                )
            else:
                click.echo("  -> 既存の雛形を保持しました。変更があればファイルを手動で更新してください。")

        click.echo("テンプレ stage（抽出＋検証）が完了しました。")

        if not result.release:
            return

        click.echo("テンプレ stage（抽出＋検証＋リリース）が完了しました。")

    return template


__all__ = ["create_template_command"]
