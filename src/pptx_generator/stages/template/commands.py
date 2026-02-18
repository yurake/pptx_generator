from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import click
from .extraction import (
    TemplateExtractionResult,
    echo_template_extraction_result,
    run_template_extraction,
)


@dataclass(slots=True)
class TemplateCommandConfig:
    template_path: Path
    output_dir: Path
    format: str
    layout: Optional[str]
    anchor: Optional[str]
    layout_mode: str
    static_source: str
    slide_snapshot: bool = False
    force: bool = False


@dataclass(slots=True)
class TemplateCommandResult:
    extraction: TemplateExtractionResult


class TemplateCommandError(Exception):
    """template / tpl-extract コマンド実行時の失敗を表す例外。"""

    def __init__(self, message: str, *, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def run_template_command(config: TemplateCommandConfig) -> TemplateCommandResult:
    try:
        extraction_result = run_template_extraction(
            template_path=config.template_path,
            output_dir=config.output_dir,
            layout=config.layout,
            anchor=config.anchor,
            output_format=config.format,
            layout_mode=config.layout_mode,
            static_source=config.static_source,
            skip_validation=config.force,
            emit_slide_snapshot=config.slide_snapshot,
        )
    except FileNotFoundError as exc:
        raise TemplateCommandError(f"ファイルが見つかりません: {exc}", exit_code=4) from exc
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, click.exceptions.Exit):
            raise
        raise TemplateCommandError(f"テンプレート抽出に失敗しました: {exc}", exit_code=1) from exc

    echo_template_extraction_result(extraction_result)

    if extraction_result.template_spec.errors:
        raise TemplateCommandError(
            "テンプレート仕様にエラーが含まれています。出力ファイルを確認してください。",
            exit_code=6,
        )

    return TemplateCommandResult(extraction=extraction_result)
