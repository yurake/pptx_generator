from __future__ import annotations

from pathlib import Path

import click

from pptx_generator.stages.prepare.handler import SLIDE_INPUTS_FILENAME
from pptx_generator.stages.prepare.models import PrepareCommandConfig
from pptx_generator.executive_board.common.script_runner import run_prepare_scripts


def normalize_prepare_inputs(prepare_inputs: tuple[str, ...]) -> list[str]:
    normalized_inputs: list[str] = []
    for raw in prepare_inputs:
        parts = [item.strip() for item in raw.split(",") if item.strip()]
        if parts:
            normalized_inputs.extend(parts)
    return normalized_inputs


def determine_primary_prepare_path(normalized_inputs: list[str]) -> Path | None:
    for candidate in normalized_inputs:
        candidate_path = Path(candidate).expanduser()
        if candidate_path.exists() and candidate_path.is_file():
            return candidate_path
    return None


def build_prepare_config(
    *,
    prepare_path: Path | None,
    prepare_inputs: tuple[str, ...],
    output_dir: Path,
    jobspec: Path | None,
    mode: str,
    page_limit: int | None,
    default_jobspec_path: Path,
    prompts_dirname: Path,
    slide_inputs_filename: Path,
) -> PrepareCommandConfig:
    return PrepareCommandConfig(
        prepare_path=prepare_path,
        prepare_inputs=prepare_inputs,
        output_dir=output_dir,
        jobspec_path=jobspec,
        mode=mode,
        page_limit=page_limit,
        default_jobspec_path=default_jobspec_path,
        prompts_dirname=prompts_dirname,
        slide_inputs_filename=slide_inputs_filename,
    )


def create_prepare_command(
    *,
    default_output_dir: Path,
    default_jobspec_path: Path,
    prompts_dirname: Path,
    slide_inputs_filename: Path = SLIDE_INPUTS_FILENAME,
) -> click.Command:
    @click.command("prepare")
    @click.argument(
        "prepare_inputs",
        nargs=-1,
        type=str,
    )
    @click.option(
        "--output",
        "-o",
        "output_dir",
        type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
        default=default_output_dir,
        show_default=True,
        help="コンテンツ準備成果物を保存するディレクトリ",
    )
    @click.option(
        "--mode",
        type=click.Choice(["static"], case_sensitive=False),
        required=True,
        help="カード生成モード。static のみ利用可能",
    )
    @click.option(
        "--jobspec",
        type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
        default=None,
        help="参照する jobspec.json (未指定時は .pptx/template/jobspec.json を探索)",
    )
    @click.option(
        "-p",
        "--page-limit",
        "--card-limit",
        type=click.IntRange(1, None),
        default=None,
        help="生成するカード枚数の上限",
    )
    def prepare(  # type: ignore[function-uses-closure]
        prepare_inputs: tuple[str, ...],
        output_dir: Path,
        jobspec: Path | None,
        mode: str,
        page_limit: int | None,
    ) -> None:
        """stage 2 コンテンツ準備: PrepareCard 成果物を生成する。"""

        normalized_inputs = normalize_prepare_inputs(prepare_inputs)
        jobspec_path = jobspec or default_jobspec_path
        if page_limit is not None:
            click.echo("page_limit はサポートされません", err=True)

        if mode.lower() != "static":
            click.echo("mode は static のみ利用可能です", err=True)
            raise click.exceptions.Exit(code=2)

        run_prepare_scripts(
            output_dir=output_dir,
            jobspec_path=jobspec_path,
            prepare_inputs=normalized_inputs,
            context_path=None,
        )

        cards_path = output_dir / "prepare_card.json"
        if cards_path.exists():
            click.echo(f"Prepare Card: {cards_path}")
        else:
            click.echo("prepare_card.json が生成されませんでした", err=True)

    return prepare


__all__ = [
    "build_prepare_config",
    "create_prepare_command",
]
