from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import click

from pptx_generator.layout_validation import (
    LayoutValidationError,
    LayoutValidationOptions,
    LayoutValidationResult,
    LayoutValidationSuite,
)


@dataclass(slots=True)
class LayoutValidateCommandConfig:
    template_path: Path
    output_dir: Path
    template_id: str | None
    baseline: Path | None
    analyzer_snapshot: Path | None


class LayoutValidateCommandError(Exception):
    """layout-validate コマンドの失敗を表す例外。"""

    def __init__(self, message: str, *, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def run_layout_validate_command(config: LayoutValidateCommandConfig) -> LayoutValidationResult:
    options = LayoutValidationOptions(
        template_path=config.template_path,
        output_dir=config.output_dir,
        template_id=config.template_id,
        baseline_path=config.baseline,
        analyzer_snapshot_path=config.analyzer_snapshot,
    )
    suite = LayoutValidationSuite(options)

    try:
        return suite.run()
    except LayoutValidationError as exc:
        raise LayoutValidateCommandError(f"レイアウト検証に失敗しました: {exc}", exit_code=6) from exc


def echo_layout_validation_result(result: LayoutValidationResult) -> None:
    click.echo(f"Layouts: {result.layouts_path}")
    click.echo(f"Diagnostics: {result.diagnostics_path}")
    if result.diff_report_path is not None:
        click.echo(f"Diff: {result.diff_report_path}")
    click.echo(
        "検出結果: warnings=%d, errors=%d"
        % (result.warnings_count, result.errors_count),
    )
