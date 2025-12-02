from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from pptx_generator.cli_handlers.rendering import (
    GenerateCommandConfig,
    GenerateCommandError,
    echo_render_outputs,
    run_generate_command,
)


def create_gen_command(
    *,
    default_output_dir: Path,
    default_pptx_name: str,
    default_rules_path: Path,
    default_pdf_output: str,
    default_pdf_timeout: int,
    default_pdf_retries: int,
) -> click.Command:
    @click.command("gen")
    @click.argument(
        "generate_ready_path",
        type=click.Path(exists=True, dir_okay=False,
                        readable=True, path_type=Path),
    )
    @click.option(
        "--output",
        "-o",
        "output_dir",
        type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
        default=default_output_dir,
        show_default=True,
        help="生成物を保存するディレクトリ",
    )
    @click.option(
        "--pptx-name",
        default=default_pptx_name,
        show_default=True,
        help="出力 PPTX のファイル名",
    )
    @click.option(
        "--rules",
        type=click.Path(exists=True, dir_okay=False,
                        readable=True, path_type=Path),
        default=default_rules_path,
        show_default=True,
        help="検証ルール設定ファイル",
    )
    @click.option(
        "--export-pdf",
        is_flag=True,
        help="LibreOffice を利用して PDF を追加出力する",
    )
    @click.option(
        "--pdf-mode",
        type=click.Choice(["both", "only"], case_sensitive=False),
        default="both",
        show_default=True,
        help="PDF 出力時の挙動。only では PPTX を保存しない",
    )
    @click.option(
        "--pdf-output",
        type=str,
        default=default_pdf_output,
        show_default=True,
        help="出力 PDF ファイル名",
    )
    @click.option(
        "--libreoffice-path",
        type=click.Path(exists=True, dir_okay=False,
                        readable=True, path_type=Path),
        default=None,
        help="LibreOffice (soffice) 実行ファイルのパス",
    )
    @click.option(
        "--pdf-timeout",
        type=int,
        default=default_pdf_timeout,
        show_default=True,
        help="LibreOffice 変換のタイムアウト秒",
    )
    @click.option(
        "--pdf-retries",
        type=int,
        default=default_pdf_retries,
        show_default=True,
        help="PDF 変換のリトライ回数",
    )
    @click.option(
        "--polisher/--no-polisher",
        "polisher_toggle",
        default=None,
        help="Open XML Polisher を明示的に有効化 / 無効化する",
    )
    @click.option(
        "--polisher-path",
        type=click.Path(exists=True, dir_okay=False,
                        readable=True, path_type=Path),
        default=None,
        help="Open XML Polisher 実行ファイルのパス",
    )
    @click.option(
        "--polisher-rules",
        type=click.Path(exists=True, dir_okay=False,
                        readable=True, path_type=Path),
        default=None,
        help="Open XML Polisher のルール設定ファイル",
    )
    @click.option(
        "--polisher-timeout",
        type=int,
        default=None,
        help="Open XML Polisher 実行のタイムアウト秒",
    )
    @click.option(
        "--polisher-arg",
        "polisher_args",
        multiple=True,
        help="Polisher に追加引数を渡す（複数指定可 / {pptx}, {rules} プレースホルダー対応）",
    )
    @click.option(
        "--polisher-cwd",
        type=click.Path(exists=True, file_okay=False,
                        dir_okay=True, path_type=Path),
        default=None,
        help="Polisher 実行時のカレントディレクトリ",
    )
    @click.option(
        "--emit-structure-snapshot",
        is_flag=True,
        help="Analyzer の構造スナップショット (analysis_snapshot.json) を出力する",
    )
    def gen(  # noqa: PLR0913
        generate_ready_path: Path,
        output_dir: Path,
        pptx_name: str,
        rules: Path,
        export_pdf: bool,
        pdf_mode: str,
        pdf_output: str,
        libreoffice_path: Optional[Path],
        pdf_timeout: int,
        pdf_retries: int,
        polisher_toggle: bool | None,
        polisher_path: Optional[Path],
        polisher_rules: Optional[Path],
        polisher_timeout: Optional[int],
        polisher_args: tuple[str, ...],
        polisher_cwd: Optional[Path],
        emit_structure_snapshot: bool,
    ) -> None:
        """generate_ready.json から PPTX / PDF / 監査ログを生成する。"""

        config = GenerateCommandConfig(
            generate_ready_path=generate_ready_path,
            output_dir=output_dir,
            pptx_name=pptx_name,
            rules_path=rules,
            export_pdf=export_pdf,
            pdf_mode=pdf_mode,
            pdf_output=pdf_output,
            libreoffice_path=libreoffice_path,
            pdf_timeout=pdf_timeout,
            pdf_retries=pdf_retries,
            polisher_toggle=polisher_toggle,
            polisher_path=polisher_path,
            polisher_rules=polisher_rules,
            polisher_timeout=polisher_timeout,
            polisher_args=polisher_args,
            polisher_cwd=polisher_cwd,
            emit_structure_snapshot=emit_structure_snapshot,
        )
        try:
            result = run_generate_command(config)
        except GenerateCommandError as exc:
            message = str(exc)
            if message:
                click.echo(message, err=True)
            raise click.exceptions.Exit(code=exc.exit_code) from exc

        echo_render_outputs(result.context, result.audit_path)

    return gen


__all__ = ["create_gen_command"]
