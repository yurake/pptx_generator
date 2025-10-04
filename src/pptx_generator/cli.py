"""pptx_generator CLI。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import typer

from .models import JobSpec, SpecValidationError
from .pipeline import (
    PipelineContext,
    PipelineRunner,
    RenderingOptions,
    SimpleAnalyzerStep,
    SimpleRendererStep,
    SpecValidatorStep,
)
from .settings import BrandingConfig, RulesConfig

DEFAULT_RULES_PATH = Path("config/rules.json")
DEFAULT_BRANDING_PATH = Path("config/branding.json")

app = typer.Typer(help="JSON 仕様から PPTX を生成する CLI")


@app.callback()
def configure_logging(
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="冗長ログ出力レベル"),
) -> None:
    level = logging.WARNING
    if verbose == 1:
        level = logging.INFO
    elif verbose >= 2:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s - %(message)s")


@app.command()
def run(
    spec_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="入力 JSON ファイル"),
    workdir: Path = typer.Option(Path(".pptxgen"), "--workdir", "-w", help="作業ディレクトリ"),
    template: Optional[Path] = typer.Option(None, "--template", "-t", exists=True, file_okay=True, dir_okay=False, readable=True, help="PPTX テンプレートファイル"),
    output_filename: str = typer.Option("proposal.pptx", "--output", "-o", help="出力 PPTX 名"),
    rules_path: Path = typer.Option(DEFAULT_RULES_PATH, "--rules", help="検証ルール設定ファイル"),
    branding_path: Path = typer.Option(DEFAULT_BRANDING_PATH, "--branding", help="ブランド設定ファイル"),
) -> None:
    """生成パイプラインを実行する。"""
    try:
        spec = JobSpec.parse_file(spec_path)
    except SpecValidationError as exc:
        _echo_errors("スキーマ検証に失敗しました", exc.errors)
        raise typer.Exit(code=2) from exc

    rules_config = RulesConfig.load(rules_path)
    branding_config = BrandingConfig.load(branding_path)

    workdir.mkdir(parents=True, exist_ok=True)
    context = PipelineContext(spec=spec, workdir=workdir)

    renderer = SimpleRendererStep(
        RenderingOptions(
            template_path=template,
            output_filename=output_filename,
            default_font_name=branding_config.body_font,
            default_font_color=branding_config.primary_color,
        )
    )
    steps = [
        SpecValidatorStep(
            max_title_length=rules_config.max_title_length,
            max_bullet_length=rules_config.max_bullet_length,
            max_bullet_level=rules_config.max_bullet_level,
            forbidden_words=rules_config.forbidden_words,
        ),
        renderer,
        SimpleAnalyzerStep(),
    ]
    runner = PipelineRunner(steps)

    try:
        runner.execute(context)
    except SpecValidationError as exc:
        _echo_errors("業務ルール検証に失敗しました", exc.errors)
        raise typer.Exit(code=3) from exc
    except FileNotFoundError as exc:
        typer.echo(f"ファイルが見つかりません: {exc}", err=True)
        raise typer.Exit(code=4) from exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("パイプライン実行中にエラーが発生しました")
        raise typer.Exit(code=1) from exc

    pptx_path = context.artifacts.get("pptx_path")
    analysis_path = context.artifacts.get("analysis_path")
    typer.echo(f"PPTX: {pptx_path}")
    typer.echo(f"Analysis: {analysis_path}")


def _echo_errors(message: str, errors: list[dict[str, object]] | None) -> None:
    typer.echo(message, err=True)
    if not errors:
        return
    formatted = json.dumps(errors, ensure_ascii=False, indent=2)
    typer.echo(formatted, err=True)


if __name__ == "__main__":
    app()
