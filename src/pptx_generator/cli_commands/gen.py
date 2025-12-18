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
from pptx_generator.runtime.job_queue import run_job_sync

from pptx_generator.cli_hooks import (
    STAGE_GEN,
    slide_contexts_from_generate_ready,
    extract_template_id_from_json_file,
    load_hooks_for_template_id,
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

        hook_manager = None
        template_id = extract_template_id_from_json_file(generate_ready_path)
        if template_id:
            hook_manager = load_hooks_for_template_id(template_id)
        stage_env = {
            "PPTX_STAGE": STAGE_GEN,
            "PPTX_GENERATE_READY_PATH": str(generate_ready_path.resolve()),
            "PPTX_OUTPUT_DIR": str(output_dir.resolve()),
            "PPTX_PPTX_NAME": pptx_name,
            "PPTX_RULES_PATH": str(rules.resolve()),
            "PPTX_EXPORT_PDF": "1" if export_pdf else "0",
            "PPTX_PDF_MODE": pdf_mode,
            "PPTX_PDF_OUTPUT": pdf_output,
            "PPTX_LIBREOFFICE_PATH": str(libreoffice_path.resolve()) if libreoffice_path else "",
            "PPTX_PDF_TIMEOUT": str(pdf_timeout),
            "PPTX_PDF_RETRIES": str(pdf_retries),
            "PPTX_POLISHER_TOGGLE": (
                "1" if polisher_toggle else "0" if polisher_toggle is not None else ""
            ),
            "PPTX_POLISHER_PATH": str(polisher_path.resolve()) if polisher_path else "",
            "PPTX_POLISHER_RULES": str(polisher_rules.resolve()) if polisher_rules else "",
            "PPTX_POLISHER_TIMEOUT": str(polisher_timeout) if polisher_timeout else "",
            "PPTX_POLISHER_ARGS": " ".join(polisher_args) if polisher_args else "",
            "PPTX_POLISHER_CWD": str(polisher_cwd.resolve()) if polisher_cwd else "",
            "PPTX_EMIT_STRUCTURE_SNAPSHOT": "1" if emit_structure_snapshot else "0",
        }
        if template_id:
            stage_env["PPTX_TEMPLATE_ID"] = template_id
        if hook_manager:
            executed, continue_default = hook_manager.run_stage_hook(
                STAGE_GEN,
                env=stage_env,
            )
            if executed:
                click.echo(
                    f"[hooks] gen stage executed via external hook (template_id={template_id})"
                )
                if not continue_default:
                    return

        contexts = slide_contexts_from_generate_ready(generate_ready_path)
        if hook_manager:
            executed = hook_manager.run_slide_hooks(
                STAGE_GEN,
                slides=contexts,
                env=stage_env,
                continue_default_filter=False,
                allow_fallback_context=True,
            )
            if executed:
                return

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
            result = run_job_sync(
                stage="gen",
                func=lambda: run_generate_command(config),
            )
        except GenerateCommandError as exc:
            message = str(exc)
            if message:
                click.echo(message, err=True)
            raise click.exceptions.Exit(code=exc.exit_code) from exc

        echo_render_outputs(result.context, result.audit_path)

        if hook_manager and template_id:
            stage_env_with_outputs = dict(stage_env)
            pptx_path = output_dir / pptx_name
            stage_env_with_outputs["PPTX_OUTPUT_PPTX_PATH"] = str(pptx_path.resolve())
            if export_pdf:
                pdf_path = output_dir / pdf_output
                stage_env_with_outputs["PPTX_OUTPUT_PDF_PATH"] = str(pdf_path.resolve())
            contexts = slide_contexts_from_generate_ready(generate_ready_path)
            hook_manager.run_slide_hooks(
                STAGE_GEN,
                slides=contexts,
                env=stage_env_with_outputs,
                continue_default_filter=True,
                allow_fallback_context=True,
            )

    return gen


__all__ = ["create_gen_command"]
