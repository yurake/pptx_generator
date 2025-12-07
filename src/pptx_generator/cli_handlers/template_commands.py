from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import click

from pptx_generator.layout_validation import LayoutValidationError

from .template_extraction import (
    TemplateExtractionResult,
    echo_template_extraction_result,
    run_template_extraction,
)
from .template_release import (
    TemplateReleaseExecutionResult,
    echo_template_release_result,
    run_template_release,
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
    template_ai_policy: Path | None
    template_ai_policy_id: str | None
    disable_template_ai: bool
    with_release: bool
    brand: str | None
    version: str | None
    template_id: str | None
    release_output: Path
    generated_by: str | None
    reviewed_by: str | None
    baseline_release: Path | None
    golden_specs: Tuple[Path, ...]
    slide_snapshot: bool = False
    force: bool = False


@dataclass(slots=True)
class TemplateCommandResult:
    extraction: TemplateExtractionResult
    release: TemplateReleaseExecutionResult | None


@dataclass(slots=True)
class TemplateReleaseCommandConfig:
    template_path: Path
    brand: str
    version: str
    template_id: str | None
    output_dir: Path
    generated_by: str | None
    reviewed_by: str | None
    baseline_release: Path | None
    golden_specs: Tuple[Path, ...]
    layout_mode: str


@dataclass(slots=True)
class TemplateExtractCommandConfig:
    template_path: Path
    output_dir: Path
    format: str
    layout: Optional[str]
    anchor: Optional[str]
    layout_mode: str
    static_source: str
    template_ai_policy: Path | None
    template_ai_policy_id: str | None
    disable_template_ai: bool


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
            template_ai_policy=config.template_ai_policy,
            template_ai_policy_id=config.template_ai_policy_id,
            disable_template_ai=config.disable_template_ai,
            layout_mode=config.layout_mode,
            static_source=config.static_source,
            skip_validation=config.force,
            emit_slide_snapshot=config.slide_snapshot,
        )
    except FileNotFoundError as exc:
        raise TemplateCommandError(f"ファイルが見つかりません: {exc}", exit_code=4) from exc
    except LayoutValidationError as exc:
        raise TemplateCommandError(f"レイアウト検証に失敗しました: {exc}", exit_code=6) from exc
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, click.exceptions.Exit):
            raise
        raise TemplateCommandError(f"テンプレート抽出に失敗しました: {exc}", exit_code=1) from exc

    echo_template_extraction_result(extraction_result)

    validation_result = extraction_result.validation_result
    if validation_result is not None and validation_result.errors_count > 0:
        raise TemplateCommandError(
            "レイアウト検証でエラーが検出されました。Diagnostics を確認してください。",
            exit_code=6,
        )
    if validation_result is None and not config.force:
        raise TemplateCommandError(
            "レイアウト検証を実施できませんでした。--force を使用しない場合は出力を確認してください。",
            exit_code=6,
        )
    if extraction_result.template_spec.errors:
        raise TemplateCommandError(
            "テンプレート仕様にエラーが含まれています。出力ファイルを確認してください。",
            exit_code=6,
        )

    if not config.with_release:
        return TemplateCommandResult(extraction=extraction_result, release=None)

    if config.brand is None or config.version is None:
        raise TemplateCommandError(
            "--with-release を使用する場合は --brand と --version を指定してください。",
            exit_code=2,
        )

    try:
        release_result = run_template_release(
            template_path=config.template_path,
            brand=config.brand,
            version=config.version,
            template_id=config.template_id,
            output_dir=config.release_output,
            generated_by=config.generated_by,
            reviewed_by=config.reviewed_by,
            baseline_release=config.baseline_release,
            golden_specs=config.golden_specs,
            layout_mode=config.layout_mode,
        )
    except FileNotFoundError as exc:
        raise TemplateCommandError(f"ファイルが見つかりません: {exc}", exit_code=4) from exc
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, click.exceptions.Exit):
            raise
        raise TemplateCommandError(f"テンプレートリリースの生成に失敗しました: {exc}", exit_code=1) from exc

    echo_template_release_result(release_result)
    if release_result.release.diagnostics.errors:
        raise TemplateCommandError(
            "テンプレートリリースの検証でエラーが検出されました。",
            exit_code=6,
        )

    return TemplateCommandResult(extraction=extraction_result, release=release_result)


def run_template_release_command(config: TemplateReleaseCommandConfig) -> TemplateReleaseExecutionResult:
    try:
        result = run_template_release(
            template_path=config.template_path,
            brand=config.brand,
            version=config.version,
            template_id=config.template_id,
            output_dir=config.output_dir,
            generated_by=config.generated_by,
            reviewed_by=config.reviewed_by,
            baseline_release=config.baseline_release,
            golden_specs=config.golden_specs,
            layout_mode=config.layout_mode,
        )
    except FileNotFoundError as exc:
        raise TemplateCommandError(f"ファイルが見つかりません: {exc}", exit_code=4) from exc
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, click.exceptions.Exit):
            raise
        raise TemplateCommandError(f"テンプレートリリースの生成に失敗しました: {exc}", exit_code=1) from exc

    if result.release.diagnostics.errors:
        raise TemplateCommandError(
            "テンプレートリリースの検証でエラーが検出されました。",
            exit_code=6,
        )

    return result


def run_template_extract_command(config: TemplateExtractCommandConfig) -> TemplateExtractionResult:
    try:
        result = run_template_extraction(
            template_path=config.template_path,
            output_dir=config.output_dir,
            layout=config.layout,
            anchor=config.anchor,
            output_format=config.format,
            template_ai_policy=config.template_ai_policy,
            template_ai_policy_id=config.template_ai_policy_id,
            disable_template_ai=config.disable_template_ai,
            layout_mode=config.layout_mode,
            static_source=config.static_source,
        )
    except FileNotFoundError as exc:
        raise TemplateCommandError(f"ファイルが見つかりません: {exc}", exit_code=4) from exc
    except LayoutValidationError as exc:
        raise TemplateCommandError(f"レイアウト検証に失敗しました: {exc}", exit_code=6) from exc
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, click.exceptions.Exit):
            raise
        raise TemplateCommandError(f"テンプレート抽出に失敗しました: {exc}", exit_code=1) from exc

    echo_template_extraction_result(result)
    validation_result = result.validation_result
    if validation_result is not None and validation_result.errors_count > 0:
        raise TemplateCommandError(
            "レイアウト検証でエラーが検出されました。Diagnostics を確認してください。",
            exit_code=6,
        )
    if result.template_spec.errors:
        raise TemplateCommandError(
            "テンプレート仕様にエラーが含まれています。出力ファイルを確認してください。",
            exit_code=6,
        )

    return result
