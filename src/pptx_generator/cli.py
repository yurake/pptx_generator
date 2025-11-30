"""pptx_generator CLI."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import click
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from .branding_extractor import extract_branding_config
from .cli_handlers import (
    PROMPT_USER_SECTION_END,
    PROMPT_USER_SECTION_START,
    SLIDE_INPUTS_FILENAME,
    PrepareCommandConfig,
    PrepareCommandError,
    build_prompt_identifier,
    _load_prompt_overrides,
    run_prepare_command,
    slugify_prompt_layout,
)
from .draft_intel import load_return_reasons
from .layout_validation import (LayoutValidationError, LayoutValidationOptions,
                                LayoutValidationResult, LayoutValidationSuite)
from .models import (ContentApprovalDocument, DraftDocument, GenerateReadyDocument,
                     JobSpec, JobSpecScaffold, SpecValidationError,
                     TemplateBlueprint, TemplateBlueprintSlide, TemplateSpec,
                     TemplateStyle)
from .pipeline import (AnalyzerOptions, ContentApprovalOptions,
                       ContentApprovalStep, DraftStructuringOptions,
                       DraftStructuringStep, MonitoringIntegrationOptions, MonitoringIntegrationStep,
                       PdfExportError, PdfExportOptions, PdfExportStep,
                       PipelineContext, PipelineRunner, PipelineStep,
                       PolisherError, PolisherOptions, PolisherStep,
                       PrepareNormalizationError, PrepareNormalizationOptions,
                       PrepareNormalizationStep, RefinerOptions,
                       RenderingAuditOptions, RenderingAuditStep,
                       RenderingOptions, SimpleAnalyzerStep, SimpleRefinerStep,
                       SimpleRendererStep, SpecValidatorStep)
from .pipeline.draft_structuring import DraftStructuringError
from .settings import RulesConfig
from .cli_handlers.common import dump_json, load_jobspec, resolve_layouts_path
from .cli_handlers.mapping import (
    MappingPipelineConfig,
    TemplateStylePayload,
    build_refiner_options,
    echo_mapping_outputs,
    prepare_template_style,
    run_mapping_pipeline,
)
from .cli_handlers.outline import (
    OutlineCommandConfig,
    OutlineResult,
    execute_outline,
    print_outline_result,
    run_draft_pipeline,
    run_outline_command,
)
from .cli_handlers.template_release import (
    TemplateReleaseExecutionResult,
    echo_template_release_result,
    resolve_template_id,
    run_template_release,
)
from .cli_handlers.template_extraction import (
    PROMPT_TEMPLATE_DIRNAME,
    TemplateExtractionResult,
    echo_template_extraction_result,
    run_template_extraction,
)
from .cli_handlers.rendering import (
    build_analyzer_options,
    build_polisher_options,
    echo_render_outputs,
    emit_review_engine_analysis,
    run_render_pipeline,
    write_audit_log,
)
from .template_style import extract_template_style

DEFAULT_RULES_PATH = Path("config/rules.json")
DEFAULT_CHAPTER_TEMPLATES_DIR = Path("config/chapter_templates")
DEFAULT_RETURN_REASONS_PATH = Path("config/return_reasons.json")
DEFAULT_PREPARE_POLICY_PATH = Path("config/prepare_policies/default.json")
DEFAULT_PREPARE_OUTPUT_DIR = Path(".pptx/prepare")
DEFAULT_JOBSPEC_PATH = Path(".pptx/extract/jobspec.json")

logger = logging.getLogger(__name__)

_LOG_LEVEL_ALIASES = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "warn": logging.WARNING,
    "error": logging.ERROR,
    "err": logging.ERROR,
    "fatal": logging.CRITICAL,
    "critical": logging.CRITICAL,
}


_DEFAULT_DRAFT_OPTIONS = DraftStructuringOptions()
DEFAULT_DRAFT_FILENAME = _DEFAULT_DRAFT_OPTIONS.draft_filename
DEFAULT_APPROVED_FILENAME = _DEFAULT_DRAFT_OPTIONS.approved_filename
DEFAULT_DRAFT_LOG_FILENAME = _DEFAULT_DRAFT_OPTIONS.log_filename
DEFAULT_GENERATE_READY_FILENAME = _DEFAULT_DRAFT_OPTIONS.generate_ready_filename
DEFAULT_GENERATE_READY_META_FILENAME = _DEFAULT_DRAFT_OPTIONS.generate_ready_meta_filename
DEFAULT_DRAFT_META_FILENAME = "draft_meta.json"


load_dotenv()


def _parse_log_level(value: str | None) -> int | None:
    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    lowered = candidate.lower()
    if lowered in _LOG_LEVEL_ALIASES:
        return _LOG_LEVEL_ALIASES[lowered]
    try:
        numeric_level = int(candidate)
    except ValueError:
        return None
    return numeric_level


def _determine_log_level(verbose: bool, debug: bool) -> tuple[int, list[tuple[int, str]]]:
    """CLI 全体のログレベルを決定する。"""
    deferred_logs: list[tuple[int, str]] = []

    if debug:
        return logging.DEBUG, deferred_logs
    if verbose:
        return logging.INFO, deferred_logs

    env_level = os.getenv("LOG_LEVEL")
    parsed_level = _parse_log_level(env_level)
    if env_level:
        if parsed_level is not None:
            return parsed_level, deferred_logs
        deferred_logs.append(
            (
                logging.WARNING,
                f"LOG_LEVEL='{env_level}' を解釈できません。WARNING レベルにフォールバックします。",
            )
        )

    if os.getenv("OPENAI_LOG"):
        deferred_logs.append(
            (
                logging.WARNING,
                "OPENAI_LOG 環境変数は廃止されました。LOG_LEVEL を利用してください。",
            )
        )

    return logging.WARNING, deferred_logs


def _configure_llm_logger() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    llm_logger = logging.getLogger("pptx_generator.slide_ai.llm")

    class _LLMLogFormatter(logging.Formatter):
        """slide_ai ログ用の安全なフォーマッタ。"""

        def __init__(self, *args, max_chars: int = 2000, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self._max_chars = max_chars

        def _sanitize(self, value: object) -> str:
            if value is None:
                return "-"
            text = str(value).replace("\n", "\\n")
            if len(text) > self._max_chars:
                return f"{text[: self._max_chars]}...(truncated)"
            return text

        def format(self, record: logging.LogRecord) -> str:  # noqa: D401
            for attr in ("slide_id", "card_id", "model", "intent", "reason", "finish_reason", "refusal"):
                if not hasattr(record, attr):
                    setattr(record, attr, "-")

            record.warnings = self._sanitize(getattr(record, "warnings", None))
            record.prompt_excerpt = self._sanitize(getattr(record, "prompt", None))
            record.raw_response_excerpt = self._sanitize(getattr(record, "raw_response", None))

            return super().format(record)

    formatter = _LLMLogFormatter(
        fmt=(
            "%(asctime)s %(levelname)s %(name)s "
            "slide_id=%(slide_id)s card_id=%(card_id)s model=%(model)s intent=%(intent)s "
            "reason=%(reason)s finish=%(finish_reason)s refusal=%(refusal)s warnings=%(warnings)s "
                "message=%(message)s prompt=%(prompt_excerpt)s raw_response=%(raw_response_excerpt)s"
        ),
    )
    class _LLMLogFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return bool(getattr(record, "raw_response", None) or getattr(record, "prompt", None))

    if not any(isinstance(f, _LLMLogFilter) for f in llm_logger.filters):
        llm_logger.addFilter(_LLMLogFilter())

    existing_handler = next(
        (
            handler
            for handler in llm_logger.handlers
            if isinstance(handler, logging.FileHandler)
            and getattr(handler, "baseFilename", None) == str(log_dir / "out.log")
        ),
        None,
    )
    if existing_handler:
        existing_handler.setFormatter(formatter)
    else:
        handler = logging.FileHandler(log_dir / "out.log", encoding="utf-8")
        handler.setFormatter(formatter)
        llm_logger.addHandler(handler)

    stream_handler_exists = any(
        isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
        for handler in llm_logger.handlers
    )
    if not stream_handler_exists:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        llm_logger.addHandler(stream_handler)
    llm_logger.setLevel(logging.INFO)
    llm_logger.propagate = False


def _log_current_llm_provider(context: str) -> None:
    provider_env = os.getenv("PPTX_LLM_PROVIDER")
    provider = provider_env.strip().lower() if provider_env else "mock"
    source = "env" if provider_env else "default"
    logging.getLogger("pptx_generator.cli.llm").info(
        "LLM provider (%s): %s (source=%s)", context, provider, source
    )


def _configure_file_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    file_path = log_dir / "out.log"
    root_logger = logging.getLogger()
    if not any(
        isinstance(handler, logging.FileHandler)
        and getattr(handler, "baseFilename", None) == str(file_path)
        for handler in root_logger.handlers
    ):
        handler = logging.FileHandler(file_path, encoding="utf-8")
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s")
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)


def _prepare_template_style(template: Path) -> tuple[TemplateStyle, dict[str, object]]:
    style, artifact = extract_template_style(template)
    if artifact.get("source", {}).get("type") == "default":
        error = artifact["source"].get("error")
        if error:
            click.echo(f"テンプレートスタイルの抽出に失敗しました: {error}", err=True)
    return style, artifact


@click.group(
    help="JSON 仕様から PPTX を生成する CLI",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("-v", "--verbose", is_flag=True, help="INFO レベルの冗長ログを出力する")
@click.option("--debug", is_flag=True, help="DEBUG レベルで詳細ログを出力する")
def app(verbose: bool, debug: bool) -> None:
    """CLI ルートエントリ。"""
    level, deferred_logs = _determine_log_level(verbose, debug)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        force=True,
    )
    logging.getLogger("openai").setLevel(level)
    cli_logger = logging.getLogger("pptx_generator.cli")
    for message_level, message in deferred_logs:
        cli_logger.log(message_level, message)
    _configure_llm_logger()
    _configure_file_logging()
def _resolve_template_path(
    *,
    spec: JobSpec,
    spec_source: Path,
) -> Path:
    """ジョブスペックとオプションからテンプレートパスを決定する。"""

    template_path_value: str | None = None
    meta = getattr(spec, "meta", None)
    if meta is not None:
        template_path_value = getattr(meta, "template_path", None)
        if template_path_value is None and isinstance(meta, BaseModel):
            extra = getattr(meta, "model_extra", None)
            if isinstance(extra, dict):
                template_path_value = extra.get("template_path")
        if template_path_value is None and isinstance(meta, dict):
            template_path_value = meta.get("template_path")

    if not template_path_value:
        try:
            raw_spec = json.loads(spec_source.read_text(encoding="utf-8"))
            template_path_value = raw_spec.get("meta", {}).get("template_path")
        except Exception:  # noqa: BLE001
            template_path_value = None

    if not template_path_value:
        raise ValueError(
            "jobspec.meta.template_path にテンプレートパスを設定してください。"
        )

    candidate_raw = Path(template_path_value)
    if candidate_raw.is_absolute():
        resolved = candidate_raw
    else:
        spec_relative = (spec_source.parent / candidate_raw).resolve()
        cwd_relative = (Path.cwd() / candidate_raw).resolve()
        if spec_relative.exists():
            resolved = spec_relative
        elif cwd_relative.exists():
            resolved = cwd_relative
        else:
            raise ValueError(
                "jobspec.meta.template_path にテンプレートパスを設定してください。"
                f"（確認したパス: {spec_relative}, {cwd_relative}）"
            )
    if not resolved.exists():
        raise ValueError(f"テンプレートファイルが見つかりません: {resolved}")
    return resolved


def _build_analyzer_options(
    rules_config: RulesConfig,
   template_style: TemplateStyle,
   emit_structure_snapshot: bool,
) -> AnalyzerOptions:
    return build_analyzer_options(
        rules_config,
        template_style,
        emit_structure_snapshot=emit_structure_snapshot,
    )


def _build_refiner_options(
    rules_config: RulesConfig,
    template_style: TemplateStyle,
) -> RefinerOptions:
    return build_refiner_options(rules_config, template_style)


def _build_polisher_options(
    rules_config: RulesConfig,
    *,
    polisher_toggle: bool | None,
    polisher_path: Optional[Path],
    polisher_rules: Optional[Path],
    polisher_timeout: Optional[int],
    polisher_args: tuple[str, ...],
    polisher_cwd: Optional[Path],
    rules_path: Path,
) -> PolisherOptions:
    return build_polisher_options(
        rules_config,
        polisher_toggle=polisher_toggle,
        polisher_path=polisher_path,
        polisher_rules=polisher_rules,
        polisher_timeout=polisher_timeout,
        polisher_args=polisher_args,
        polisher_cwd=polisher_cwd,
        rules_path=rules_path,
    )




def _run_content_approval_pipeline(
    *,
    spec: JobSpec,
    output_dir: Path,
    content_approved: Path | None,
    content_review_log: Path | None,
    require_document: bool,
) -> PipelineContext:
    output_dir.mkdir(parents=True, exist_ok=True)
    context = PipelineContext(spec=spec, workdir=output_dir)

    step = ContentApprovalStep(
        ContentApprovalOptions(
            approved_path=content_approved,
            review_log_path=content_review_log,
            require_document=require_document,
            require_all_approved=True,
        )
    )
    PipelineRunner([step]).execute(context)
    return context


def _write_content_outputs(
    *,
    context: PipelineContext,
    output_dir: Path,
    spec_filename: str,
    content_filename: str,
    review_filename: str,
    meta_filename: str,
) -> tuple[Path, Path | None, Path | None, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    spec_path = output_dir / spec_filename
    dump_json(spec_path, context.spec.model_dump(mode="json"))

    content_document = context.artifacts.get("content_approved")
    content_path: Path | None = None
    if isinstance(content_document, ContentApprovalDocument):
        content_path = output_dir / content_filename
        dump_json(content_path, content_document.model_dump(mode="json"))

    review_logs = context.artifacts.get("content_review_log")
    review_path: Path | None = None
    if review_logs:
        review_payload: list[dict[str, object]] = []
        for entry in review_logs:
            if hasattr(entry, "model_dump"):
                review_payload.append(entry.model_dump(
                    mode="json"))  # type: ignore[call-arg]
            else:
                review_payload.append(entry)
        review_path = output_dir / review_filename
        dump_json(review_path, review_payload)

    content_meta = context.artifacts.get("content_approved_meta")
    review_meta = context.artifacts.get("content_review_log_meta")
    meta_payload: dict[str, object] = {
        "spec": {
            "slides": len(context.spec.slides),
            "output_path": str(spec_path),
        }
    }
    if isinstance(content_meta, dict):
        meta_payload["content_approved"] = {
            **content_meta,
            "output_path": str(content_path) if content_path else None,
        }
    if isinstance(review_meta, dict):
        meta_payload["content_review_log"] = {
            **review_meta,
            "output_path": str(review_path) if review_path else None,
        }

    meta_path = output_dir / meta_filename
    dump_json(meta_path, meta_payload)

    return spec_path, content_path, review_path, meta_path
    if not show_layout_reasons:
        return

    draft_document = result.context.artifacts.get("draft_document")
    if not isinstance(draft_document, DraftDocument):
        return

    click.echo("layout_hint 候補スコア内訳:")
    for section in draft_document.sections:
        for slide in section.slides:
            detail = slide.layout_score_detail
            if not detail:
                continue
            click.echo(
                f"- {slide.ref_id} -> {slide.layout_hint} "
                f"(uses_tag={detail.uses_tag:.2f}, "
                f"capacity={detail.content_capacity:.2f}, "
                f"diversity={detail.diversity:.2f}, "
                f"analyzer={detail.analyzer_support:.2f})"
            )



def _run_render_pipeline(
    *,
    generate_ready: GenerateReadyDocument,
    generate_ready_path: Optional[Path],
    output_dir: Path,
    template: Optional[Path],
    pptx_name: str,
    template_style: TemplateStyle,
    template_style_artifact: dict[str, object],
    analyzer_options: AnalyzerOptions,
    pdf_options: PdfExportOptions,
    polisher_options: PolisherOptions | None = None,
    base_artifacts: dict[str, object] | None = None,
) -> PipelineContext:
    return run_render_pipeline(
        generate_ready=generate_ready,
        generate_ready_path=generate_ready_path,
        output_dir=output_dir,
        template=template,
        pptx_name=pptx_name,
        template_style=template_style,
        template_style_artifact=template_style_artifact,
        analyzer_options=analyzer_options,
        pdf_options=pdf_options,
        polisher_options=polisher_options,
        base_artifacts=base_artifacts,
    )


def _echo_render_outputs(context: PipelineContext, audit_path: Path | None) -> None:
    echo_render_outputs(context, audit_path)


@app.command("gen")
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
    default=Path(".pptx/gen"),
    show_default=True,
    help="生成物を保存するディレクトリ",
)
@click.option(
    "--pptx-name",
    default="proposal.pptx",
    show_default=True,
    help="出力 PPTX のファイル名",
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
@click.option(
    "--polisher/--no-polisher",
    "polisher_toggle",
    default=None,
    help="Open XML Polisher を実行するかを明示的に指定する（設定ファイル値を上書き）",
)
@click.option(
    "--polisher-path",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    default=None,
    help="Open XML Polisher (.exe / .dll) もしくはラッパースクリプトのパス",
)
@click.option(
    "--polisher-rules",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    default=None,
    help="Polisher へ渡すルール設定ファイル",
)
@click.option(
    "--polisher-timeout",
    type=int,
    default=None,
    help="Polisher 実行のタイムアウト秒（設定ファイル値を上書き）",
)
@click.option(
    "--polisher-arg",
    "polisher_args",
    multiple=True,
    help="Polisher へ渡す追加引数（{pptx}, {rules} をプレースホルダーとして利用可能）",
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

    if not export_pdf and pdf_mode != "both":
        click.echo("--pdf-mode は --export-pdf と併用してください", err=True)
        raise click.exceptions.Exit(code=2)

    try:
        generate_ready = GenerateReadyDocument.parse_file(generate_ready_path)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"generate_ready.json の読み込みに失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc

    template_path_str = generate_ready.meta.template_path
    if not template_path_str:
        click.echo(
            "generate_ready.json に template_path が含まれていません。stage 4 を最新仕様で再実行するか、テンプレート情報を埋め込んでください。",
            err=True,
        )
        raise click.exceptions.Exit(code=2)

    template_path = Path(template_path_str)
    if not template_path.is_absolute():
        candidate = (generate_ready_path.parent / template_path).resolve()
        template_path = candidate if candidate.exists() else template_path
    if not template_path.exists():
        click.echo(f"テンプレートファイルが見つかりません: {template_path}", err=True)
        raise click.exceptions.Exit(code=4)

    rules_config = RulesConfig.load(rules)
    template_style, template_style_artifact = _prepare_template_style(template_path)
    analyzer_options = _build_analyzer_options(
        rules_config, template_style, emit_structure_snapshot
    )
    pdf_options = PdfExportOptions(
        enabled=export_pdf,
        mode=pdf_mode,
        output_filename=pdf_output,
        soffice_path=libreoffice_path,
        timeout_sec=pdf_timeout,
        max_retries=pdf_retries,
    )
    polisher_options = _build_polisher_options(
        rules_config,
        polisher_toggle=polisher_toggle,
        polisher_path=polisher_path,
        polisher_rules=polisher_rules,
        polisher_timeout=polisher_timeout,
        polisher_args=polisher_args,
        polisher_cwd=polisher_cwd,
        rules_path=rules,
    )

    mapping_meta: dict[str, object] = {
        "generate_ready_path": str(generate_ready_path),
        "generate_ready_generated_at": generate_ready.meta.generated_at,
        "template_version": generate_ready.meta.template_version,
        "template_path": str(template_path),
    }

    base_artifacts: dict[str, object] = {
        "generate_ready": generate_ready,
        "generate_ready_path": str(generate_ready_path),
        "mapping_meta": mapping_meta,
    }

    mapping_log_path = generate_ready_path.with_name("mapping_log.json")
    if mapping_log_path.exists():
        base_artifacts["mapping_log_path"] = str(mapping_log_path)
        try:
            mapping_log = json.loads(
                mapping_log_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("mapping_log.json の読み込みに失敗しました: %s", exc)
        else:
            meta_payload = mapping_log.get("meta")
            if isinstance(meta_payload, dict):
                mapping_meta.update(meta_payload)
    fallback_path = generate_ready_path.with_name("fallback_report.json")
    if fallback_path.exists():
        base_artifacts["mapping_fallback_report_path"] = str(fallback_path)

    try:
        render_context = _run_render_pipeline(
            generate_ready=generate_ready,
            generate_ready_path=generate_ready_path,
            output_dir=output_dir,
            template=template_path,
            pptx_name=pptx_name,
            template_style=template_style,
            template_style_artifact=template_style_artifact,
            analyzer_options=analyzer_options,
            pdf_options=pdf_options,
            polisher_options=polisher_options,
            base_artifacts=base_artifacts,
        )
    except PdfExportError as exc:
        click.echo(f"PDF 出力に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=5) from exc
    except PolisherError as exc:
        click.echo(f"Polisher の実行に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=6) from exc
    except FileNotFoundError as exc:
        click.echo(f"ファイルが見つかりません: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("パイプライン実行中にエラーが発生しました")
        raise click.exceptions.Exit(code=1) from exc

    analysis_path = render_context.artifacts.get("analysis_path")
    _emit_review_engine_analysis(render_context, analysis_path)
    audit_path = _write_audit_log(render_context)
    _echo_render_outputs(render_context, audit_path)


@app.command("prepare")
@click.argument(
    "prepare_path",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    required=False,
)
@click.option(
    "--output",
    "-o",
    "output_dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=DEFAULT_PREPARE_OUTPUT_DIR,
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
def prepare(
    prepare_path: Path | None,
    output_dir: Path,
    jobspec: Path | None,
    mode: str,
    page_limit: int | None,
) -> None:
    """stage 2 コンテンツ準備: PrepareCard 成果物を生成する。"""

    config = PrepareCommandConfig(
        prepare_path=prepare_path,
        output_dir=output_dir,
        jobspec_path=jobspec,
        mode=mode,
        page_limit=page_limit,
        policy_path=DEFAULT_PREPARE_POLICY_PATH,
        default_jobspec_path=DEFAULT_JOBSPEC_PATH,
        prompts_dirname=PROMPT_TEMPLATE_DIRNAME,
        slide_inputs_filename=SLIDE_INPUTS_FILENAME,
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


@app.command("outline")
@click.argument(
    "spec_path",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
)
@click.option(
    "--output",
    "-o",
    "output_dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".pptx/draft"),
    show_default=True,
    help="ドラフト成果物を保存するディレクトリ",
)
@click.option(
    "--target-length",
    type=int,
    default=None,
    help="目標スライド枚数",
)
@click.option(
    "--structure-pattern",
    type=str,
    default=None,
    help="章構成パターン名",
)
@click.option(
    "--appendix-limit",
    type=int,
    default=5,
    show_default=True,
    help="付録枚数の上限",
)
@click.option(
    "--chapter-templates-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=DEFAULT_CHAPTER_TEMPLATES_DIR,
    show_default=True,
    help="章テンプレート辞書ディレクトリ",
)
@click.option(
    "--chapter-template",
    type=str,
    default=None,
    help="適用する章テンプレート ID",
)
@click.option(
    "--import-analysis",
    "analysis_summary_path",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    default=None,
    help="analysis_summary.json のパス",
)
@click.option(
    "--return-reasons-path",
    type=click.Path(dir_okay=False, writable=False, path_type=Path),
    default=DEFAULT_RETURN_REASONS_PATH,
    show_default=True,
    help="差戻し理由テンプレート辞書のパス",
)
@click.option(
    "--return-reasons",
    is_flag=True,
    default=False,
    help="差戻し理由テンプレート一覧を表示して終了する",
)
@click.option(
    "--show-layout-reasons",
    is_flag=True,
    default=False,
    help="layout_hint 候補のスコア内訳を表示する",
)
@click.option(
    "--prepare-cards",
    type=click.Path(exists=False, dir_okay=False,
                    readable=True, path_type=Path),
    default=DEFAULT_PREPARE_OUTPUT_DIR / "prepare_card.json",
    show_default=True,
    help="stage 2 の prepare_card.json",
)
def outline(
    spec_path: Path,
    output_dir: Path,
    target_length: int | None,
    structure_pattern: str | None,
    appendix_limit: int,
    chapter_templates_dir: Path,
    chapter_template: str | None,
    analysis_summary_path: Path | None,
    return_reasons_path: Path,
    return_reasons: bool,
    show_layout_reasons: bool,
    prepare_cards: Path,
) -> None:
    """stage 4 ドラフト構成（アウトライン）を生成する。"""

    config = OutlineCommandConfig(
        spec_path=spec_path,
        output_dir=output_dir,
        target_length=target_length,
        structure_pattern=structure_pattern,
        appendix_limit=appendix_limit,
        chapter_templates_dir=chapter_templates_dir,
        chapter_template=chapter_template,
        analysis_summary_path=analysis_summary_path,
        prepare_cards=prepare_cards,
        require_prepare=True,
        return_reasons_path=return_reasons_path,
        return_reasons=return_reasons,
        show_layout_reasons=show_layout_reasons,
        draft_filename=DEFAULT_DRAFT_FILENAME,
        approved_filename=DEFAULT_APPROVED_FILENAME,
        log_filename=DEFAULT_DRAFT_LOG_FILENAME,
        generate_ready_filename=DEFAULT_GENERATE_READY_FILENAME,
        generate_ready_meta_filename=DEFAULT_GENERATE_READY_META_FILENAME,
        meta_filename=DEFAULT_DRAFT_META_FILENAME,
    )

    try:
        run_outline_command(config)
    except PrepareNormalizationError as exc:
        click.echo(f"プレペア成果物の読み込みに失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except DraftStructuringError as exc:
        click.echo(f"ドラフト構成の生成に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc


@app.command("compose")
@click.argument(
    "spec_path",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
)
@click.option(
    "--draft-output",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".pptx/draft"),
    show_default=True,
    help="ドラフト成果物を保存するディレクトリ",
)
@click.option(
    "--target-length",
    type=int,
    default=None,
    help="目標スライド枚数",
)
@click.option(
    "--structure-pattern",
    type=str,
    default=None,
    help="章構成パターン名",
)
@click.option(
    "--appendix-limit",
    type=int,
    default=5,
    show_default=True,
    help="付録枚数の上限",
)
@click.option(
    "--chapter-templates-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=DEFAULT_CHAPTER_TEMPLATES_DIR,
    show_default=True,
    help="章テンプレート辞書ディレクトリ",
)
@click.option(
    "--chapter-template",
    type=str,
    default=None,
    help="適用する章テンプレート ID",
)
@click.option(
    "--import-analysis",
    "analysis_summary_path",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    default=None,
    help="analysis_summary.json のパス",
)
@click.option(
    "--show-layout-reasons",
    is_flag=True,
    default=False,
    help="layout_hint 候補のスコア内訳を表示する",
)
@click.option(
    "--output",
    "-o",
    "output_dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".pptx/compose"),
    show_default=True,
    help="generate_ready.json 等の出力ディレクトリ",
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
    "--prepare-cards",
    "prepare_cards",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    default=DEFAULT_PREPARE_OUTPUT_DIR / "prepare_card.json",
    show_default=True,
    help="stage 2 の prepare_card.json",
)
def compose(  # noqa: PLR0913
    spec_path: Path,
    draft_output: Path,
    target_length: int | None,
    structure_pattern: str | None,
    appendix_limit: int,
    chapter_templates_dir: Path,
    chapter_template: str | None,
    analysis_summary_path: Path | None,
    show_layout_reasons: bool,
    output_dir: Path,
    rules: Path,
    prepare_cards: Path,
) -> None:
    """stage 4+5 を連続実行しドラフトとマッピング成果物を生成する。"""

    try:
        spec = _load_jobspec(spec_path)
    except SpecValidationError as exc:
        _echo_errors("スキーマ検証に失敗しました", exc.errors)
        raise click.exceptions.Exit(code=2) from exc

    try:
        resolved_template = _resolve_template_path(
            spec=spec,
            spec_source=spec_path,
        )
    except ValueError as exc:
        click.echo(str(exc), err=True)
        raise click.exceptions.Exit(code=2) from exc
    try:
        resolved_layouts = _resolve_layouts_path(
            spec=spec,
            spec_source=spec_path,
        )
    except ValueError as exc:
        click.echo(str(exc), err=True)
        raise click.exceptions.Exit(code=2) from exc

    templates_dir = chapter_templates_dir if chapter_templates_dir.exists() else None

    try:
        outline_result = _execute_outline(
            spec=spec,
            layouts=resolved_layouts,
            output_dir=draft_output,
            spec_source_path=spec_path,
            target_length=target_length,
            structure_pattern=structure_pattern,
            appendix_limit=appendix_limit,
            chapter_templates_dir=templates_dir,
            chapter_template=chapter_template,
            analysis_summary_path=analysis_summary_path,
            prepare_cards=prepare_cards,
            require_prepare=True,
            draft_filename=DEFAULT_DRAFT_FILENAME,
            approved_filename=DEFAULT_APPROVED_FILENAME,
            log_filename=DEFAULT_DRAFT_LOG_FILENAME,
            generate_ready_filename=DEFAULT_GENERATE_READY_FILENAME,
            generate_ready_meta_filename=DEFAULT_GENERATE_READY_META_FILENAME,
            meta_filename=DEFAULT_DRAFT_META_FILENAME,
        )
    except PrepareNormalizationError as exc:
        click.echo(f"プレペア成果物の読み込みに失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except DraftStructuringError as exc:
        click.echo(f"ドラフト構成の生成に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except FileNotFoundError as exc:
        click.echo(f"ファイルが見つかりません: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("compose 実行中にアウトライン stage でエラーが発生しました")
        raise click.exceptions.Exit(code=1) from exc

    _print_outline_result(outline_result, show_layout_reasons=show_layout_reasons)

    rules_config = RulesConfig.load(rules)
    style, artifact = _prepare_template_style(resolved_template)
    template_style_payload = TemplateStylePayload(style=style, artifact=artifact)
    refiner_options = _build_refiner_options(rules_config, template_style_payload.style)

    mapping_params = MappingPipelineConfig(
        spec=spec,
        output_dir=output_dir,
        spec_source_path=spec_path,
        rules_config=rules_config,
        refiner_options=refiner_options,
        template_style=template_style_payload,
        prepare_cards=prepare_cards,
        require_prepare=True,
        layouts=resolved_layouts,
        draft_output=draft_output,
        template=resolved_template,
    )

    try:
        mapping_context = _run_mapping_pipeline(
            params=mapping_params,
            draft_context=outline_result.context,
            draft_options=DraftStructuringOptions(
                layouts_path=resolved_layouts,
                output_dir=draft_output,
                spec_source_path=spec_path,
                target_length=target_length,
                structure_pattern=structure_pattern,
                appendix_limit=appendix_limit,
                chapter_templates_dir=chapter_templates_dir,
                chapter_template_id=chapter_template,
                analysis_summary_path=analysis_summary_path,
            ),
        )
    except ValueError as exc:
        click.echo(str(exc), err=True)
        raise click.exceptions.Exit(code=2) from exc
    except SpecValidationError as exc:
        _echo_errors("業務ルール検証に失敗しました", exc.errors)
        raise click.exceptions.Exit(code=3) from exc
    except PrepareNormalizationError as exc:
        click.echo(f"プレペア成果物の読み込みに失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("compose 実行中にマッピング stage でエラーが発生しました")
        raise click.exceptions.Exit(code=1) from exc

    echo_mapping_outputs(mapping_context)


@app.command("mapping")
@click.argument(
    "spec_path",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
)
@click.option(
    "--output",
    "-o",
    "output_dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".pptx/gen"),
    show_default=True,
    help="generate_ready.json 等の出力ディレクトリ",
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
    "--draft-output",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".pptx/draft"),
    show_default=True,
    help="draft_draft.json / draft_approved.json の出力先",
)
@click.option(
    "--prepare-cards",
    "prepare_cards",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    default=DEFAULT_PREPARE_OUTPUT_DIR / "prepare_card.json",
    show_default=True,
    help="stage 2 の prepare_card.json",
)
def mapping(  # noqa: PLR0913
    spec_path: Path,
    output_dir: Path,
    rules: Path,
    draft_output: Path,
    prepare_cards: Path,
) -> None:
    """stage 5 マッピングを実行し generate_ready.json を生成する。"""
    try:
        spec = _load_jobspec(spec_path)
    except SpecValidationError as exc:
        _echo_errors("スキーマ検証に失敗しました", exc.errors)
        raise click.exceptions.Exit(code=2) from exc

    try:
        resolved_template = _resolve_template_path(
            spec=spec,
            spec_source=spec_path,
        )
    except ValueError as exc:
        click.echo(str(exc), err=True)
        raise click.exceptions.Exit(code=2) from exc

    try:
        resolved_layouts = _resolve_layouts_path(
            spec=spec,
            spec_source=spec_path,
        )
    except ValueError as exc:
        click.echo(str(exc), err=True)
        raise click.exceptions.Exit(code=2) from exc

    rules_config = RulesConfig.load(rules)
    style, artifact = _prepare_template_style(resolved_template)
    template_style_payload = TemplateStylePayload(style=style, artifact=artifact)
    refiner_options = _build_refiner_options(rules_config, template_style_payload.style)

    mapping_params = MappingPipelineConfig(
        spec=spec,
        output_dir=output_dir,
        spec_source_path=spec_path,
        rules_config=rules_config,
        refiner_options=refiner_options,
        template_style=template_style_payload,
        prepare_cards=prepare_cards,
        require_prepare=True,
        layouts=resolved_layouts,
        draft_output=draft_output,
        template=resolved_template,
    )

    try:
        context = _run_mapping_pipeline(params=mapping_params)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        raise click.exceptions.Exit(code=2) from exc
    except SpecValidationError as exc:
        _echo_errors("業務ルール検証に失敗しました", exc.errors)
        raise click.exceptions.Exit(code=3) from exc
    except PrepareNormalizationError as exc:
        click.echo(f"プレペア成果物の読み込みに失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("マッピング実行中にエラーが発生しました")
        raise click.exceptions.Exit(code=1) from exc

    echo_mapping_outputs(context)


@app.command("template")
@click.argument(
    "template_path",
    type=click.Path(dir_okay=False, readable=True, path_type=Path),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".pptx/extract"),
    show_default=True,
    help="抽出・検証結果を保存するディレクトリ",
)
@click.option(
    "--format",
    type=click.Choice(["json", "yaml"], case_sensitive=False),
    default="json",
    show_default=True,
    help="テンプレート仕様の出力形式",
)
@click.option(
    "--layout",
    type=str,
    default=None,
    help="抽出対象レイアウト名のフィルタ（前方一致）",
)
@click.option(
    "--anchor",
    type=str,
    default=None,
    help="抽出対象アンカー名のフィルタ（前方一致）",
)
@click.option(
    "--layout-mode",
    type=click.Choice(["dynamic", "static"], case_sensitive=False),
    default="dynamic",
    show_default=True,
    help="テンプレートの想定運用モード。static を指定すると Blueprint を出力する",
)
@click.option(
    "--with-release",
    is_flag=True,
    help="抽出・検証後にテンプレートリリースメタも生成する",
)
@click.option(
    "--brand",
    type=str,
    default=None,
    help="--with-release 時のブランド名",
)
@click.option(
    "--version",
    type=str,
    default=None,
    help="--with-release 時のテンプレートバージョン",
)
@click.option(
    "--template-id",
    type=str,
    default=None,
    help="--with-release 時のテンプレート識別子。未指定時は <brand>_<version> を使用",
)
@click.option(
    "--release-output",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".pptx/release"),
    show_default=True,
    help="テンプレートリリース成果物の出力ディレクトリ",
)
@click.option(
    "--generated-by",
    type=str,
    default=None,
    help="テンプレートリリースメタの生成者",
)
@click.option(
    "--reviewed-by",
    type=str,
    default=None,
    help="テンプレートリリースメタのレビュー担当者",
)
@click.option(
    "--baseline-release",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    default=None,
    help="比較対象となる過去の template_release.json",
)
@click.option(
    "--golden-spec",
    "golden_specs",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    multiple=True,
    help="テンプレ互換性検証に使用する spec ファイル（複数指定可）",
)
@click.option(
    "--template-ai-policy",
    type=click.Path(dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="テンプレート usage_tags 推定に使用する AI ポリシー JSON",
)
@click.option(
    "--template-ai-policy-id",
    type=str,
    default=None,
    help="テンプレート AI ポリシーセット内の利用対象 ID",
)
@click.option(
    "--disable-template-ai",
    is_flag=True,
    default=False,
    help="生成AIによる usage_tags 推定を無効化する",
)
@click.option(
    "--slide",
    is_flag=True,
    default=False,
    help="実スライドの図形・段落情報を slide_snapshot.json として出力する",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="レイアウト検証をスキップして強制的にテンプレ stage を継続する（緊急時のみ使用）",
)
def template(  # noqa: PLR0913
    template_path: Path,
    output: Path,
    format: str,
    layout: str | None,
    anchor: str | None,
    layout_mode: str,
    with_release: bool,
    brand: str | None,
    version: str | None,
    template_id: str | None,
    release_output: Path,
    generated_by: str | None,
    reviewed_by: str | None,
    baseline_release: Path | None,
    golden_specs: tuple[Path, ...],
    template_ai_policy: Path | None,
    template_ai_policy_id: str | None,
    disable_template_ai: bool,
    slide: bool,
    force: bool,
) -> None:
    """テンプレ stage（抽出・検証・必要に応じてリリース）を実行する。"""
    _log_current_llm_provider("template")
    try:
        extraction_result = _run_template_extraction(
            template_path=template_path,
            output_dir=output,
            layout=layout,
            anchor=anchor,
            output_format=format,
            template_ai_policy=template_ai_policy,
            template_ai_policy_id=template_ai_policy_id,
            disable_template_ai=disable_template_ai,
            layout_mode=layout_mode,
            skip_validation=force,
            emit_slide_snapshot=slide,
        )
    except FileNotFoundError as exc:
        click.echo(f"ファイルが見つかりません: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except LayoutValidationError as exc:
        click.echo(f"レイアウト検証に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=6) from exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("テンプレート抽出中にエラーが発生しました")
        click.echo(f"テンプレート抽出に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=1) from exc

    _echo_template_extraction_result(extraction_result)

    validation_result = extraction_result.validation_result
    if validation_result is not None and validation_result.errors_count > 0:
        click.echo(
            "レイアウト検証でエラーが検出されました。Diagnostics を確認してください。",
            err=True,
        )
        raise click.exceptions.Exit(code=6)
    if validation_result is None and not force:
        click.echo(
            "レイアウト検証を実施できませんでした。--force を使用しない場合は出力を確認してください。",
            err=True,
        )
        raise click.exceptions.Exit(code=6)

    if extraction_result.template_spec.errors:
        click.echo(
            "テンプレート仕様にエラーが含まれています。出力ファイルを確認してください。",
            err=True,
        )
        raise click.exceptions.Exit(code=6)

    if extraction_result.prompt_templates_dir is not None:
        click.echo(
            "プロンプト雛形を出力しました: %s"
            % extraction_result.prompt_templates_dir,
        )
        if extraction_result.prompt_templates_created:
            click.echo(
                f"  -> {extraction_result.prompt_templates_created} 件のスライド雛形を生成しました。必要に応じて編集し、static prepare で反映してください。"
            )
        else:
            click.echo("  -> 既存の雛形を保持しました。変更があればファイルを手動で更新してください。")
    click.echo("テンプレ stage（抽出＋検証）が完了しました。")

    if not with_release:
        return

    if brand is None or version is None:
        raise click.UsageError(
            "--with-release を使用する場合は --brand と --version を指定してください。")

    try:
        release_result = _run_template_release(
            template_path=template_path,
            brand=brand,
            version=version,
            template_id=template_id,
            output_dir=release_output,
            generated_by=generated_by,
            reviewed_by=reviewed_by,
            baseline_release=baseline_release,
            golden_specs=golden_specs,
            layout_mode=layout_mode,
        )
    except FileNotFoundError as exc:
        click.echo(f"ファイルが見つかりません: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except click.exceptions.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        logging.exception("テンプレートリリース生成中にエラーが発生しました")
        click.echo(f"テンプレートリリースの生成に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=1) from exc

    _echo_template_release_result(release_result)
    if release_result.release.diagnostics.errors:
        raise click.exceptions.Exit(code=6)

    click.echo("テンプレ stage（抽出＋検証＋リリース）が完了しました。")


@app.command("tpl-extract")
@click.option(
    "--template",
    "-t",
    "template_path",
    type=click.Path(dir_okay=False, readable=True, path_type=Path),
    required=True,
    help="抽出対象の PPTX テンプレートファイル",
)
@click.option(
    "--layout",
    type=str,
    default=None,
    help="抽出対象レイアウト名のフィルタ（前方一致）",
)
@click.option(
    "--anchor",
    type=str,
    default=None,
    help="抽出対象アンカー名のフィルタ（前方一致）",
)
@click.option(
    "--format",
    type=click.Choice(["json", "yaml"], case_sensitive=False),
    default="json",
    show_default=True,
    help="出力形式",
)
@click.option(
    "--layout-mode",
    type=click.Choice(["dynamic", "static"], case_sensitive=False),
    default="dynamic",
    show_default=True,
    help="テンプレートの想定運用モード。static を指定すると Blueprint を出力する",
)
@click.option(
    "--output",
    "-o",
    "output_dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".pptx/extract"),
    show_default=True,
    help="テンプレート仕様とブランド設定を保存するディレクトリ",
)
@click.option(
    "--template-ai-policy",
    type=click.Path(dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="テンプレート usage_tags 推定に使用する AI ポリシー JSON",
)
@click.option(
    "--template-ai-policy-id",
    type=str,
    default=None,
    help="テンプレート AI ポリシーセット内の利用対象 ID",
)
@click.option(
    "--disable-template-ai",
    is_flag=True,
    default=False,
    help="生成AIによる usage_tags 推定を無効化する",
)
def tpl_extract(
    template_path: Path,
    output_dir: Path,
    layout: Optional[str],
    anchor: Optional[str],
    format: str,
    layout_mode: str,
    template_ai_policy: Path | None,
    template_ai_policy_id: str | None,
    disable_template_ai: bool,
) -> None:
    """テンプレートファイルから図形・プレースホルダー情報を抽出してJSON仕様の雛形を生成する。"""
    try:
        extraction_result = _run_template_extraction(
            template_path=template_path,
            output_dir=output_dir,
            layout=layout,
            anchor=anchor,
            output_format=format,
            template_ai_policy=template_ai_policy,
            template_ai_policy_id=template_ai_policy_id,
            disable_template_ai=disable_template_ai,
            layout_mode=layout_mode,
        )
    except FileNotFoundError as exc:
        click.echo(f"ファイルが見つかりません: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except LayoutValidationError as exc:
        click.echo(f"レイアウト検証に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=6) from exc
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, click.exceptions.Exit):
            raise
        logging.exception("テンプレート抽出中にエラーが発生しました")
        click.echo(f"テンプレート抽出に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=1) from exc
    else:
        _echo_template_extraction_result(extraction_result)
        validation_result = extraction_result.validation_result
        if validation_result is not None and validation_result.errors_count > 0:
            click.echo(
                "レイアウト検証でエラーが検出されました。Diagnostics を確認してください。",
                err=True,
            )
            raise click.exceptions.Exit(code=6)
        if extraction_result.template_spec.errors:
            click.echo(
                "テンプレート仕様にエラーが含まれています。出力ファイルを確認してください。",
                err=True,
            )
            raise click.exceptions.Exit(code=6)


@app.command("layout-validate")
@click.option(
    "--template",
    "-t",
    "template_path",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    required=True,
    help="検証対象の PPTX テンプレートファイル",
)
@click.option(
    "--output",
    "-o",
    "output_dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".pptx/validation"),
    show_default=True,
    help="検証成果物の出力ディレクトリ",
)
@click.option(
    "--template-id",
    type=str,
    default=None,
    help="layouts.jsonl に記録するテンプレート ID",
)
@click.option(
    "--baseline",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    default=None,
    help="比較対象となる過去の layouts.jsonl",
)
@click.option(
    "--analyzer-snapshot",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    default=None,
    help="Analyzer が出力した構造スナップショット JSON",
)
def layout_validate(
    template_path: Path,
    output_dir: Path,
    template_id: Optional[str],
    baseline: Optional[Path],
    analyzer_snapshot: Optional[Path],
) -> None:
    """テンプレート構造の検証スイートを実行する。"""

    options = LayoutValidationOptions(
        template_path=template_path,
        output_dir=output_dir,
        template_id=template_id,
        baseline_path=baseline,
        analyzer_snapshot_path=analyzer_snapshot,
    )
    suite = LayoutValidationSuite(options)

    try:
        result = suite.run()
    except LayoutValidationError as exc:
        click.echo(f"レイアウト検証に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=6) from exc

    click.echo(f"Layouts: {result.layouts_path}")
    click.echo(f"Diagnostics: {result.diagnostics_path}")
    if result.diff_report_path is not None:
        click.echo(f"Diff: {result.diff_report_path}")
    click.echo(
        "検出結果: warnings=%d, errors=%d" % (
            result.warnings_count, result.errors_count)
    )


@app.command("tpl-release")
@click.option(
    "--template",
    "-t",
    "template_path",
    type=click.Path(dir_okay=False, readable=True, path_type=Path),
    required=True,
    help="リリース対象の PPTX テンプレートファイル",
)
@click.option("--brand", type=str, required=True, help="ブランド名")
@click.option("--version", type=str, required=True, help="テンプレートバージョン")
@click.option(
    "--template-id",
    type=str,
    default=None,
    help="テンプレート識別子（未指定時は brand_version を使用）",
)
@click.option(
    "--output",
    "-o",
    "output_dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".pptx/release"),
    show_default=True,
    help="リリース成果物を保存するディレクトリ",
)
@click.option(
    "--generated-by",
    type=str,
    default=None,
    help="リリースメタの生成者",
)
@click.option(
    "--reviewed-by",
    type=str,
    default=None,
    help="レビュー担当者",
)
@click.option(
    "--baseline-release",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    default=None,
    help="比較対象となる過去の template_release.json",
)
@click.option(
    "--golden-spec",
    "golden_specs",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    multiple=True,
    help="テンプレ互換性検証に使用する spec ファイル（複数指定可）",
)
@click.option(
    "--layout-mode",
    type=click.Choice(["dynamic", "static"], case_sensitive=False),
    default="dynamic",
    show_default=True,
    help="テンプレートの想定運用モード。static を指定すると Blueprint を出力する",
)
def tpl_release(
    template_path: Path,
    brand: str,
    version: str,
    template_id: Optional[str],
    output_dir: Path,
    generated_by: Optional[str],
    reviewed_by: Optional[str],
    baseline_release: Optional[Path],
    golden_specs: tuple[Path, ...],
    layout_mode: str,
) -> None:
    """テンプレート受け渡しメタと差分レポートを生成する。"""

    try:
        result = _run_template_release(
            template_path=template_path,
            brand=brand,
            version=version,
            template_id=template_id,
            output_dir=output_dir,
            generated_by=generated_by,
            reviewed_by=reviewed_by,
            baseline_release=baseline_release,
            golden_specs=golden_specs,
            layout_mode=layout_mode,
        )
    except click.exceptions.Exit:
        raise
    except FileNotFoundError as exc:
        click.echo(f"ファイルが見つかりません: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("テンプレートリリース生成中にエラーが発生しました")
        click.echo(f"テンプレートリリースの生成に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=1) from exc
    else:
        _echo_template_release_result(result)
        if result.release.diagnostics.errors:
            raise click.exceptions.Exit(code=6)


def _echo_errors(message: str, errors: list[dict[str, object]] | None) -> None:
    click.echo(message, err=True)
    if not errors:
        return
    formatted = json.dumps(errors, ensure_ascii=False, indent=2)
    click.echo(formatted, err=True)


def _emit_review_engine_analysis(
    context: PipelineContext, analysis_path: object | None
) -> Path | None:
    return emit_review_engine_analysis(context, analysis_path)


def _write_audit_log(context: PipelineContext) -> Path:
    return write_audit_log(context)


if __name__ == "__main__":
    app()


def _execute_outline(**kwargs: object) -> OutlineResult:
    return execute_outline(**kwargs)


def _print_outline_result(result: OutlineResult, *, show_layout_reasons: bool) -> None:
    print_outline_result(result, show_layout_reasons=show_layout_reasons)


def _run_template_release(**kwargs: object) -> TemplateReleaseExecutionResult:
    return run_template_release(**kwargs)


def _echo_template_release_result(result: TemplateReleaseExecutionResult) -> None:
    echo_template_release_result(result)


def _run_template_extraction(
    *,
    template_path: Path,
    output_dir: Path,
    layout: str | None,
    anchor: str | None,
    output_format: str,
    template_ai_policy: Path | None,
    template_ai_policy_id: str | None,
    disable_template_ai: bool,
    layout_mode: str,
    skip_validation: bool = False,
    emit_slide_snapshot: bool = False,
) -> TemplateExtractionResult:
    return run_template_extraction(
        template_path=template_path,
        output_dir=output_dir,
        layout=layout,
        anchor=anchor,
        output_format=output_format,
        template_ai_policy=template_ai_policy,
        template_ai_policy_id=template_ai_policy_id,
        disable_template_ai=disable_template_ai,
        layout_mode=layout_mode,
        skip_validation=skip_validation,
        emit_slide_snapshot=emit_slide_snapshot,
    )


def _echo_template_extraction_result(result: TemplateExtractionResult) -> None:
    echo_template_extraction_result(result)


def _run_mapping_pipeline(
    *,
    params: MappingPipelineConfig,
    draft_context: PipelineContext | None = None,
    draft_options: DraftStructuringOptions | None = None,
) -> PipelineContext:
    return run_mapping_pipeline(
        params=params,
        draft_context=draft_context,
        draft_options=draft_options,
        generate_ready_filename=DEFAULT_GENERATE_READY_FILENAME,
        generate_ready_meta_filename=DEFAULT_GENERATE_READY_META_FILENAME,
    )


def _run_draft_pipeline(
    *,
    spec: JobSpec,
    output_dir: Path,
    prepare_cards: Path | None,
    require_prepare: bool,
    draft_options: DraftStructuringOptions,
) -> PipelineContext:
    return run_draft_pipeline(
        spec=spec,
        output_dir=output_dir,
        prepare_cards=prepare_cards,
        require_prepare=require_prepare,
        draft_options=draft_options,
    )


def _load_jobspec(path: Path) -> JobSpec:
    return load_jobspec(path)


def _resolve_layouts_path(*, spec: JobSpec, spec_source: Path) -> Path | None:
    return resolve_layouts_path(spec=spec, spec_source=spec_source)
