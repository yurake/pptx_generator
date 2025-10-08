"""pptx_generator CLI."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click

from .models import JobSpec, SpecValidationError
from .pipeline import (AnalyzerOptions, PdfExportError, PdfExportOptions,
                       PdfExportStep, PipelineContext, PipelineRunner,
                       RefinerOptions, RenderingOptions, SimpleAnalyzerStep,
                       SimpleRefinerStep, SimpleRendererStep, SpecValidatorStep)
from .settings import BrandingConfig, RulesConfig

DEFAULT_RULES_PATH = Path("config/rules.json")
DEFAULT_BRANDING_PATH = Path("config/branding.json")


@click.group(help="JSON 仕様から PPTX を生成する CLI")
@click.option("-v", "--verbose", is_flag=True, help="冗長ログを出力する")
def app(verbose: bool) -> None:
    """CLI ルートエントリ。"""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level, format="%(asctime)s %(levelname)s %(name)s - %(message)s")


@app.command()
@click.argument(
    "spec_path",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
)
@click.option(
    "--workdir",
    "-w",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".pptxgen"),
    show_default=True,
    help="作業ディレクトリ",
)
@click.option(
    "--template",
    "-t",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    default=None,
    help="PPTX テンプレートファイル",
)
@click.option(
    "--output",
    "-o",
    "output_filename",
    default="proposal.pptx",
    show_default=True,
    help="出力 PPTX 名",
)
@click.option(
    "--rules",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    default=DEFAULT_RULES_PATH,
    show_default=True,
    help="検証ルール設定ファイル",
)
@click.option(
    "--branding",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    default=DEFAULT_BRANDING_PATH,
    show_default=True,
    help="ブランド設定ファイル",
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
    default="proposal.pdf",
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
    default=120,
    show_default=True,
    help="LibreOffice 変換のタイムアウト秒",
)
@click.option(
    "--pdf-retries",
    type=int,
    default=2,
    show_default=True,
    help="LibreOffice 変換の最大リトライ回数",
)
def run(
    spec_path: Path,
    workdir: Path,
    template: Optional[Path],
    output_filename: str,
    rules: Path,
    branding: Path,
    export_pdf: bool,
    pdf_mode: str,
    pdf_output: str,
    libreoffice_path: Optional[Path],
    pdf_timeout: int,
    pdf_retries: int,
) -> None:
    """生成パイプラインを実行する。"""
    try:
        spec = JobSpec.parse_file(spec_path)
    except SpecValidationError as exc:
        _echo_errors("スキーマ検証に失敗しました", exc.errors)
        raise click.exceptions.Exit(code=2) from exc

    rules_config = RulesConfig.load(rules)
    branding_config = BrandingConfig.load(branding)

    workdir.mkdir(parents=True, exist_ok=True)
    context = PipelineContext(spec=spec, workdir=workdir)

    renderer = SimpleRendererStep(
        RenderingOptions(
            template_path=template,
            output_filename=output_filename,
            branding=branding_config,
        )
    )
    refiner = SimpleRefinerStep(
        RefinerOptions(
            max_bullet_level=rules_config.max_bullet_level,
        )
    )
    analyzer = SimpleAnalyzerStep(
        AnalyzerOptions(
            min_font_size=branding_config.body_font.size_pt,
            default_font_size=branding_config.body_font.size_pt,
            default_font_color=branding_config.body_font.color_hex,
            preferred_text_color=branding_config.primary_color,
            background_color=branding_config.background_color,
            max_bullet_level=rules_config.max_bullet_level,
        )
    )
    if not export_pdf and pdf_mode != "both":
        click.echo("--pdf-mode は --export-pdf と併用してください", err=True)
        raise click.exceptions.Exit(code=2)

    pdf_options = PdfExportOptions(
        enabled=export_pdf,
        mode=pdf_mode,
        output_filename=pdf_output,
        soffice_path=libreoffice_path,
        timeout_sec=pdf_timeout,
        max_retries=pdf_retries,
    )

    steps = [
        SpecValidatorStep(
            max_title_length=rules_config.max_title_length,
            max_bullet_length=rules_config.max_bullet_length,
            max_bullet_level=rules_config.max_bullet_level,
            forbidden_words=rules_config.forbidden_words,
        ),
        refiner,
        renderer,
        analyzer,
    ]
    if pdf_options.enabled:
        steps.append(PdfExportStep(pdf_options))
    runner = PipelineRunner(steps)

    try:
        runner.execute(context)
    except SpecValidationError as exc:
        _echo_errors("業務ルール検証に失敗しました", exc.errors)
        raise click.exceptions.Exit(code=3) from exc
    except FileNotFoundError as exc:
        click.echo(f"ファイルが見つかりません: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except PdfExportError as exc:
        click.echo(f"PDF 出力に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=5) from exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("パイプライン実行中にエラーが発生しました")
        raise click.exceptions.Exit(code=1) from exc

    audit_path = _write_audit_log(context)

    pptx_path = context.artifacts.get("pptx_path")
    analysis_path = context.artifacts.get("analysis_path")
    if pptx_path is not None:
        click.echo(f"PPTX: {pptx_path}")
    else:
        click.echo("PPTX: --pdf-mode=only のため保存しませんでした")
    click.echo(f"Analysis: {analysis_path}")
    pdf_path = context.artifacts.get("pdf_path")
    if pdf_path is not None:
        click.echo(f"PDF: {pdf_path}")
    click.echo(f"Audit: {audit_path}")


def _echo_errors(message: str, errors: list[dict[str, object]] | None) -> None:
    click.echo(message, err=True)
    if not errors:
        return
    formatted = json.dumps(errors, ensure_ascii=False, indent=2)
    click.echo(formatted, err=True)


def _write_audit_log(context: PipelineContext) -> Path:
    outputs_dir = context.workdir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    audit_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec_meta": context.spec.meta.model_dump(),
        "slides": len(context.spec.slides),
        "artifacts": {
            "pptx": _artifact_str(context.artifacts.get("pptx_path")),
            "analysis": _artifact_str(context.artifacts.get("analysis_path")),
            "pdf": _artifact_str(context.artifacts.get("pdf_path")),
        },
        "pdf_export": context.artifacts.get("pdf_export_metadata"),
        "refiner_adjustments": context.artifacts.get("refiner_adjustments"),
    }
    audit_path = outputs_dir / "audit_log.json"
    audit_path.write_text(json.dumps(
        audit_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    context.add_artifact("audit_path", audit_path)
    return audit_path


def _artifact_str(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)


if __name__ == "__main__":
    app()
