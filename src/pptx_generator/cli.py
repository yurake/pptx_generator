"""pptx_generator CLI."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import click

from .models import JobSpec, SpecValidationError
from .pipeline import (
    AnalyzerOptions,
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


@click.group(help="JSON 仕様から PPTX を生成する CLI")
@click.option("-v", "--verbose", is_flag=True, help="冗長ログを出力する")
def app(verbose: bool) -> None:
    """CLI ルートエントリ。"""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s - %(message)s")


@app.command()
@click.argument(
    "spec_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
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
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
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
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=DEFAULT_RULES_PATH,
    show_default=True,
    help="検証ルール設定ファイル",
)
@click.option(
    "--branding",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=DEFAULT_BRANDING_PATH,
    show_default=True,
    help="ブランド設定ファイル",
)
def run(
    spec_path: Path,
    workdir: Path,
    template: Optional[Path],
    output_filename: str,
    rules: Path,
    branding: Path,
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
            default_font_name=branding_config.body_font,
            default_font_size=branding_config.body_font_size,
            default_font_color=branding_config.primary_color,
        )
    )
    analyzer = SimpleAnalyzerStep(
        AnalyzerOptions(
            min_font_size=branding_config.body_font_size,
            default_font_size=branding_config.body_font_size,
            default_font_color=branding_config.body_font_color,
            preferred_text_color=branding_config.primary_color,
            background_color=branding_config.background_color,
            max_bullet_level=rules_config.max_bullet_level,
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
        analyzer,
    ]
    runner = PipelineRunner(steps)

    try:
        runner.execute(context)
    except SpecValidationError as exc:
        _echo_errors("業務ルール検証に失敗しました", exc.errors)
        raise click.exceptions.Exit(code=3) from exc
    except FileNotFoundError as exc:
        click.echo(f"ファイルが見つかりません: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("パイプライン実行中にエラーが発生しました")
        raise click.exceptions.Exit(code=1) from exc

    pptx_path = context.artifacts.get("pptx_path")
    analysis_path = context.artifacts.get("analysis_path")
    click.echo(f"PPTX: {pptx_path}")
    click.echo(f"Analysis: {analysis_path}")


def _echo_errors(message: str, errors: list[dict[str, object]] | None) -> None:
    click.echo(message, err=True)
    if not errors:
        return
    formatted = json.dumps(errors, ensure_ascii=False, indent=2)
    click.echo(formatted, err=True)


if __name__ == "__main__":
    app()
