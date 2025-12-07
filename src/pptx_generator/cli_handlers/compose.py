from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pptx_generator.pipeline import (
    DraftStructuringError,
    DraftStructuringOptions,
    PipelineContext,
    PrepareNormalizationError,
)
from pptx_generator.models import SpecValidationError
from pptx_generator.settings import RulesConfig
from pptx_generator.settings.loader import load_rules_config

from .common import (
    load_jobspec,
    resolve_layouts_path,
    resolve_template_path,
)
from .mapping import (
    DEFAULT_GENERATE_READY_FILENAME,
    DEFAULT_GENERATE_READY_META_FILENAME,
    MappingPipelineConfig,
    build_refiner_options,
    echo_mapping_outputs,
    prepare_template_style,
    run_mapping_pipeline,
)
from .outline import OutlineResult, execute_outline, print_outline_result

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ComposeCommandConfig:
    spec_path: Path
    draft_output: Path
    target_length: Optional[int]
    structure_pattern: Optional[str]
    appendix_limit: int
    analysis_summary_path: Optional[Path]
    show_layout_reasons: bool
    output_dir: Path
    rules_path: Path
    prepare_cards: Path
    draft_filename: str
    approved_filename: str
    log_filename: str
    meta_filename: str
    generate_ready_filename: str = DEFAULT_GENERATE_READY_FILENAME
    generate_ready_meta_filename: str = DEFAULT_GENERATE_READY_META_FILENAME


@dataclass(slots=True)
class ComposeCommandResult:
    outline: OutlineResult
    mapping_context: PipelineContext


class ComposeCommandError(Exception):
    """compose コマンド実行時の失敗を表す例外。"""

    def __init__(
        self,
        message: str,
        *,
        exit_code: int,
        errors: list[dict[str, object]] | None = None,
    ) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.errors = errors


def run_compose_command(config: ComposeCommandConfig) -> ComposeCommandResult:
    try:
        spec = load_jobspec(config.spec_path)
    except SpecValidationError as exc:
        errors = getattr(exc, "errors", None)
        raise ComposeCommandError(
            "スキーマ検証に失敗しました",
            exit_code=2,
            errors=errors,
        ) from exc

    try:
        resolved_template = resolve_template_path(spec=spec, spec_source=config.spec_path)
    except ValueError as exc:
        raise ComposeCommandError(str(exc), exit_code=2) from exc

    try:
        resolved_layouts = resolve_layouts_path(spec=spec, spec_source=config.spec_path)
    except ValueError as exc:
        raise ComposeCommandError(str(exc), exit_code=2) from exc

    try:
        outline_result = execute_outline(
            spec=spec,
            layouts=resolved_layouts,
            output_dir=config.draft_output,
            spec_source_path=config.spec_path,
            target_length=config.target_length,
            structure_pattern=config.structure_pattern,
            appendix_limit=config.appendix_limit,
            analysis_summary_path=config.analysis_summary_path,
            prepare_cards=config.prepare_cards,
            require_prepare=True,
            draft_filename=config.draft_filename,
            approved_filename=config.approved_filename,
            log_filename=config.log_filename,
            generate_ready_filename=config.generate_ready_filename,
            generate_ready_meta_filename=config.generate_ready_meta_filename,
            meta_filename=config.meta_filename,
        )
    except PrepareNormalizationError as exc:
        raise ComposeCommandError(
            f"プレペア成果物の読み込みに失敗しました: {exc}",
            exit_code=4,
        ) from exc
    except DraftStructuringError as exc:
        raise ComposeCommandError(
            f"ドラフト構成の生成に失敗しました: {exc}",
            exit_code=4,
        ) from exc
    except FileNotFoundError as exc:
        raise ComposeCommandError(f"ファイルが見つかりません: {exc}", exit_code=4) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("compose 実行中にアウトライン stage でエラーが発生しました")
        raise ComposeCommandError("compose 実行中にアウトライン stage でエラーが発生しました", exit_code=1) from exc

    print_outline_result(outline_result, show_layout_reasons=config.show_layout_reasons)

    rules_config = load_rules_config(config.rules_path)
    template_style_payload = prepare_template_style(resolved_template)
    refiner_options = build_refiner_options(rules_config, template_style_payload.style)

    mapping_params = MappingPipelineConfig(
        spec=spec,
        output_dir=config.output_dir,
        spec_source_path=config.spec_path,
        rules_config=rules_config,
        refiner_options=refiner_options,
        template_style=template_style_payload,
        prepare_cards=config.prepare_cards,
        require_prepare=True,
        layouts=resolved_layouts,
        draft_output=config.draft_output,
        template=resolved_template,
    )

    draft_options = DraftStructuringOptions(
        layouts_path=resolved_layouts,
        output_dir=config.draft_output,
        spec_source_path=config.spec_path,
        target_length=config.target_length,
        structure_pattern=config.structure_pattern,
        appendix_limit=config.appendix_limit,
        analysis_summary_path=config.analysis_summary_path,
        draft_store_dir=(config.draft_output / "store"),
    )

    try:
        mapping_context = run_mapping_pipeline(
            params=mapping_params,
            draft_context=outline_result.context,
            draft_options=draft_options,
            generate_ready_filename=config.generate_ready_filename,
            generate_ready_meta_filename=config.generate_ready_meta_filename,
        )
    except ValueError as exc:
        raise ComposeCommandError(str(exc), exit_code=2) from exc
    except SpecValidationError as exc:
        raise ComposeCommandError(
            "業務ルール検証に失敗しました",
            exit_code=3,
            errors=exc.errors,
        ) from exc
    except PrepareNormalizationError as exc:
        raise ComposeCommandError(
            f"プレペア成果物の読み込みに失敗しました: {exc}",
            exit_code=4,
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("compose 実行中にマッピング stage でエラーが発生しました")
        raise ComposeCommandError("compose 実行中にマッピング stage でエラーが発生しました", exit_code=1) from exc

    echo_mapping_outputs(mapping_context)

    return ComposeCommandResult(outline=outline_result, mapping_context=mapping_context)
