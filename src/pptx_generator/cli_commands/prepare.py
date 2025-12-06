from __future__ import annotations

from pathlib import Path

import click

from pptx_generator.cli_handlers import (
    SLIDE_INPUTS_FILENAME,
    PrepareCommandConfig,
    PrepareCommandError,
    run_prepare_command,
)
from pptx_generator.cli_handlers.common import dump_json


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
        type=click.Choice(["dynamic", "static"], case_sensitive=False),
        required=True,
        help="カード生成モード。static は Blueprint を利用する",
    )
    @click.option(
        "--jobspec",
        type=click.Path(exists=True, dir_okay=False,
                        readable=True, path_type=Path),
        default=None,
        help="静的モードで参照する jobspec.json (未指定時は .pptx/extract/jobspec.json を探索)",
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

        normalized_inputs: list[str] = []
        for raw in prepare_inputs:
            parts = [item.strip() for item in raw.split(",") if item.strip()]
            if parts:
                normalized_inputs.extend(parts)

        primary_prepare_path: Path | None = None
        for candidate in normalized_inputs:
            candidate_path = Path(candidate).expanduser()
            if candidate_path.exists() and candidate_path.is_file():
                primary_prepare_path = candidate_path
                break

        config = build_prepare_config(
            prepare_path=primary_prepare_path,
            prepare_inputs=tuple(normalized_inputs),
            output_dir=output_dir,
            jobspec=jobspec,
            mode=mode,
            page_limit=page_limit,
            default_jobspec_path=default_jobspec_path,
            prompts_dirname=prompts_dirname,
            slide_inputs_filename=slide_inputs_filename,
        )
        try:
            result = run_prepare_command(config, dump_json=dump_json)
        except PrepareCommandError as exc:
            click.echo(str(exc), err=True)
            raise click.exceptions.Exit(code=exc.exit_code) from exc

        for message in result.messages:
            click.echo(message)

        click.echo(f"Prepare Card: {result.cards_path}")
        click.echo(f"Prepare Log: {result.log_path}")
        click.echo(f"Prepare AI Log: {result.ai_log_path}")
        click.echo(f"AI Generation Meta: {result.meta_path}")
        click.echo(f"Prepare Story Outline: {result.story_outline_path}")
        click.echo(f"Audit Log: {result.audit_path}")

    return prepare


__all__ = [
    "build_prepare_config",
    "create_prepare_command",
]
