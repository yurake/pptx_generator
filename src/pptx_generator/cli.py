"""pptx_generator CLI."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

from .branding_extractor import (
    BrandingExtractionError,
    extract_branding_config,
)
from .content_ai import (ContentAIOrchestrationError, ContentAIOrchestrator,
                         ContentAIPolicyError, LLMClientConfigurationError,
                         MockLLMClient, create_llm_client, load_policy_set)
from .content_import import ContentImportError, ContentImportService
from .layout_validation import (LayoutValidationError, LayoutValidationOptions,
                                LayoutValidationSuite)
from .models import (ContentApprovalDocument, DraftDocument, JobSpec,
                     GenerateReadyDocument, SpecValidationError, TemplateRelease,
                     TemplateReleaseDiagnostics, TemplateReleaseGoldenRun)
from .pipeline import (AnalyzerOptions, ContentApprovalError,
                       ContentApprovalOptions, ContentApprovalStep,
                       DraftStructuringOptions, DraftStructuringStep,
                       MappingOptions, MappingStep, MonitoringIntegrationOptions,
                       MonitoringIntegrationStep, PdfExportError,
                       PdfExportOptions, PdfExportStep, PipelineContext,
                       PipelineRunner, PipelineStep, PolisherError, PolisherOptions,
                       PolisherStep, RefinerOptions, RenderingAuditOptions,
                       RenderingAuditStep, RenderingOptions, SimpleAnalyzerStep,
                       SimpleRefinerStep, SimpleRendererStep, SpecValidatorStep,
                       TemplateExtractor, TemplateExtractorOptions)
from .pipeline.draft_structuring import DraftStructuringError
from .review_engine import AnalyzerReviewEngineAdapter
from .template_audit import (build_release_report, build_template_release,
                             load_template_release)
from .settings import BrandingConfig, RulesConfig
from .generate_ready import generate_ready_to_jobspec
from .draft_intel import load_return_reasons

DEFAULT_RULES_PATH = Path("config/rules.json")
DEFAULT_BRANDING_PATH = Path("config/branding.json")
DEFAULT_CHAPTER_TEMPLATES_DIR = Path("config/chapter_templates")
DEFAULT_RETURN_REASONS_PATH = Path("config/return_reasons.json")
DEFAULT_AI_POLICY_PATH = Path("config/content_ai_policies.json")

logger = logging.getLogger(__name__)


load_dotenv()


def _configure_llm_logger() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    llm_logger = logging.getLogger("pptx_generator.content_ai.llm")
    if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == str(log_dir / "out.log") for h in llm_logger.handlers):
        handler = logging.FileHandler(log_dir / "out.log", encoding="utf-8")
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        handler.setFormatter(formatter)
        llm_logger.addHandler(handler)
    llm_logger.setLevel(logging.INFO)
    llm_logger.propagate = False


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
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)


def _resolve_config_path(value: str, *, base_dir: Path | None = None) -> Path:
    """設定ファイルで指定されたパスを解決する。"""
    candidate = Path(value)
    if candidate.is_absolute():
        resolved = candidate
    else:
        if candidate.parts and candidate.parts[0] == "config":
            resolved = Path.cwd() / candidate
        elif base_dir is not None:
            resolved = base_dir / candidate
        else:
            resolved = Path.cwd() / candidate
    resolved = resolved.resolve()
    if not resolved.exists():
        msg = f"設定ファイルで指定されたパスが見つかりません: {resolved}"
        raise FileNotFoundError(msg)
    return resolved


@click.group(help="JSON 仕様から PPTX を生成する CLI")
@click.option("-v", "--verbose", is_flag=True, help="INFO レベルの冗長ログを出力する")
@click.option("--debug", is_flag=True, help="DEBUG レベルで詳細ログを出力する")
def app(verbose: bool, debug: bool) -> None:
    """CLI ルートエントリ。"""
    level = logging.DEBUG if debug else logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    _configure_llm_logger()
    _configure_file_logging()


def _prepare_branding(
    template: Optional[Path], branding: Optional[Path]
) -> tuple[BrandingConfig, dict[str, object]]:
    def _load_default_branding() -> tuple[BrandingConfig, dict[str, object]]:
        try:
            config = BrandingConfig.load(DEFAULT_BRANDING_PATH)
            return config, {"type": "default", "path": str(DEFAULT_BRANDING_PATH)}
        except FileNotFoundError:
            click.echo(
                f"デフォルトのブランド設定が見つかりません: {DEFAULT_BRANDING_PATH}. 内蔵設定を使用します。",
                err=True,
            )
            return BrandingConfig.default(), {"type": "builtin"}

    branding_payload: dict[str, object] | None = None
    if branding is not None:
        branding_config = BrandingConfig.load(branding)
        branding_source = {"type": "file", "path": str(branding)}
    elif template is not None:
        try:
            extraction = extract_branding_config(template)
        except BrandingExtractionError as exc:
            click.echo(f"ブランド設定の抽出に失敗しました: {exc}", err=True)
            branding_config, branding_source = _load_default_branding()
            branding_source["error"] = str(exc)
        else:
            branding_config = extraction.to_branding_config()
            branding_payload = extraction.to_branding_payload()
            branding_source = {"type": "template", "template": str(template)}
    else:
        branding_config, branding_source = _load_default_branding()

    artifact = {"source": branding_source}
    if branding_payload is not None:
        artifact["config"] = branding_payload
    return branding_config, artifact


def _build_reference_text(document: ContentApprovalDocument) -> tuple[str | None, bool]:
    lines: list[str] = []
    for slide in document.slides:
        if slide.elements.title:
            lines.append(str(slide.elements.title))
        lines.extend(str(item) for item in slide.elements.body)
        if slide.elements.note:
            lines.append(str(slide.elements.note))

    reference_text = "\n".join(line.strip() for line in lines if line.strip())
    if not reference_text:
        return None, False

    return reference_text, False


def _build_analyzer_options(
    rules_config: RulesConfig,
    branding_config: BrandingConfig,
    emit_structure_snapshot: bool,
) -> AnalyzerOptions:
    analyzer_rules = rules_config.analyzer
    analyzer_defaults = AnalyzerOptions()
    body_font_size = branding_config.body_font.size_pt
    body_font_color = branding_config.body_font.color_hex
    primary_color = branding_config.primary_color
    background_color = branding_config.background_color

    return AnalyzerOptions(
        min_font_size=analyzer_rules.min_font_size
        if analyzer_rules.min_font_size is not None
        else body_font_size,
        default_font_size=analyzer_rules.default_font_size
        if analyzer_rules.default_font_size is not None
        else body_font_size,
        default_font_color=analyzer_rules.default_font_color or body_font_color,
        preferred_text_color=analyzer_rules.preferred_text_color or primary_color,
        background_color=analyzer_rules.background_color or background_color,
        min_contrast_ratio=analyzer_rules.min_contrast_ratio
        if analyzer_rules.min_contrast_ratio is not None
        else analyzer_defaults.min_contrast_ratio,
        large_text_min_contrast=analyzer_rules.large_text_min_contrast
        if analyzer_rules.large_text_min_contrast is not None
        else analyzer_defaults.large_text_min_contrast,
        large_text_threshold_pt=analyzer_rules.large_text_threshold_pt
        if analyzer_rules.large_text_threshold_pt is not None
        else body_font_size,
        margin_in=analyzer_rules.margin_in
        if analyzer_rules.margin_in is not None
        else analyzer_defaults.margin_in,
        slide_width_in=analyzer_rules.slide_width_in
        if analyzer_rules.slide_width_in is not None
        else analyzer_defaults.slide_width_in,
        slide_height_in=analyzer_rules.slide_height_in
        if analyzer_rules.slide_height_in is not None
        else analyzer_defaults.slide_height_in,
        max_bullet_level=rules_config.max_bullet_level,
        snapshot_output_filename="analysis_snapshot.json"
        if emit_structure_snapshot
        else None,
    )


def _build_refiner_options(
    rules_config: RulesConfig, branding_config: BrandingConfig
) -> RefinerOptions:
    analyzer_rules = rules_config.analyzer
    refiner_rules = rules_config.refiner
    body_font_size = branding_config.body_font.size_pt
    body_font_color = branding_config.body_font.color_hex
    primary_color = branding_config.primary_color

    return RefinerOptions(
        max_bullet_level=rules_config.max_bullet_level,
        enable_bullet_reindent=refiner_rules.enable_bullet_reindent,
        enable_font_raise=refiner_rules.enable_font_raise,
        min_font_size=refiner_rules.min_font_size
        if refiner_rules.min_font_size is not None
        else body_font_size,
        enable_color_adjust=refiner_rules.enable_color_adjust,
        preferred_text_color=refiner_rules.preferred_text_color
        or analyzer_rules.preferred_text_color
        or primary_color,
        fallback_font_color=refiner_rules.fallback_font_color or body_font_color,
        default_font_name=branding_config.body_font.name,
    )


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
    config = rules_config.polisher
    enabled = polisher_toggle if polisher_toggle is not None else config.enabled

    executable: Path | None = polisher_path
    if executable is None and config.executable:
        executable = _resolve_config_path(config.executable, base_dir=rules_path.parent)

    rules_file: Path | None = polisher_rules
    if rules_file is None and config.rules_path:
        rules_file = _resolve_config_path(config.rules_path, base_dir=rules_path.parent)

    timeout_sec = polisher_timeout or config.timeout_sec
    arguments = tuple(config.arguments) + tuple(polisher_args)

    return PolisherOptions(
        enabled=enabled,
        executable=executable,
        rules_path=rules_file,
        timeout_sec=timeout_sec,
        arguments=arguments,
        working_dir=polisher_cwd,
    )


def _dump_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")
    logger.info("Saved JSON to %s", path.resolve())


def _load_jobspec(path: Path) -> JobSpec:
    logger.info("Loading JobSpec from %s", path.resolve())
    return JobSpec.parse_file(path)


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
    _dump_json(spec_path, context.spec.model_dump(mode="json"))

    content_document = context.artifacts.get("content_approved")
    content_path: Path | None = None
    if isinstance(content_document, ContentApprovalDocument):
        content_path = output_dir / content_filename
        _dump_json(content_path, content_document.model_dump(mode="json"))

    review_logs = context.artifacts.get("content_review_log")
    review_path: Path | None = None
    if review_logs:
        review_payload: list[dict[str, object]] = []
        for entry in review_logs:
            if hasattr(entry, "model_dump"):
                review_payload.append(entry.model_dump(mode="json"))  # type: ignore[call-arg]
            else:
                review_payload.append(entry)
        review_path = output_dir / review_filename
        _dump_json(review_path, review_payload)

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
    _dump_json(meta_path, meta_payload)

    return spec_path, content_path, review_path, meta_path


def _run_draft_pipeline(
    *,
    spec: JobSpec,
    output_dir: Path,
    content_approved: Path | None,
    content_review_log: Path | None,
    draft_options: DraftStructuringOptions,
) -> PipelineContext:
    output_dir.mkdir(parents=True, exist_ok=True)

    steps: list[PipelineStep] = []
    steps.append(
        ContentApprovalStep(
            ContentApprovalOptions(
                approved_path=content_approved,
                review_log_path=content_review_log,
                require_document=content_approved is not None,
                require_all_approved=True,
                fallback_builder=ContentApprovalStep.build_document_from_spec,
            )
        )
    )
    steps.append(DraftStructuringStep(draft_options))

    context = PipelineContext(spec=spec, workdir=output_dir)
    PipelineRunner(steps).execute(context)
    return context


def _write_draft_meta(
    *,
    context: PipelineContext,
    output_dir: Path,
    meta_filename: str,
    draft_filename: str,
    approved_filename: str,
    log_filename: str,
) -> Path:
    draft_document = context.artifacts.get("draft_document")
    sections = 0
    slides = 0
    approved_sections: list[str] = []
    section_status: dict[str, str] = {}
    appendix_limit: int | None = None
    structure_pattern: str | None = None
    target_length: int | None = None
    template_id: str | None = None
    template_match_score: float | None = None
    template_mismatch: list[dict[str, object]] = []
    analyzer_summary: dict[str, int] = {}
    return_reason_stats: dict[str, int] = {}

    if isinstance(draft_document, DraftDocument):
        sections = len(draft_document.sections)
        for section in draft_document.sections:
            section_status[section.name] = section.status
            if section.status == "approved":
                approved_sections.append(section.name)
            slides += len(section.slides)
        appendix_limit = draft_document.meta.appendix_limit
        structure_pattern = draft_document.meta.structure_pattern
        target_length = draft_document.meta.target_length
        template_id = draft_document.meta.template_id
        template_match_score = draft_document.meta.template_match_score
        template_mismatch = [item.model_dump(mode="json") for item in draft_document.meta.template_mismatch]
        analyzer_summary = draft_document.meta.analyzer_summary
        return_reason_stats = draft_document.meta.return_reason_stats

    paths = {
        "draft_draft": str((output_dir / draft_filename).resolve()),
        "draft_approved": str((output_dir / approved_filename).resolve()),
        "draft_review_log": str((output_dir / log_filename).resolve()),
    }

    approved_path = context.artifacts.get("draft_document_path")
    if isinstance(approved_path, str):
        paths["draft_approved"] = str(Path(approved_path).resolve())
    log_path = context.artifacts.get("draft_review_log_path")
    if isinstance(log_path, str):
        paths["draft_review_log"] = str(Path(log_path).resolve())

    meta_payload = {
        "spec_id": context.artifacts.get("draft_spec_id"),
        "sections": sections,
        "slides": slides,
        "approved_sections": approved_sections,
        "section_status": section_status,
        "appendix_limit": appendix_limit,
        "structure_pattern": structure_pattern,
        "target_length": target_length,
        "paths": paths,
        "template": {
            "template_id": template_id,
            "match_score": template_match_score,
            "mismatch": template_mismatch,
        },
        "analyzer_summary": analyzer_summary,
        "return_reason_stats": return_reason_stats,
    }

    meta_path = output_dir / meta_filename
    _dump_json(meta_path, meta_payload)
    return meta_path


def _execute_outline(  # noqa: PLR0913
    *,
    spec: JobSpec,
    output_dir: Path,
    content_approved: Path | None,
    content_review_log: Path | None,
    layouts: Path | None,
    draft_filename: str,
    approved_filename: str,
    log_filename: str,
    meta_filename: str,
    target_length: int | None,
    structure_pattern: str | None,
    appendix_limit: int,
    chapter_templates_dir: Path,
    chapter_template: str | None,
    analysis_summary_path: Path | None,
) -> tuple[PipelineContext, Path, DraftStructuringOptions]:
    templates_dir = chapter_templates_dir if chapter_templates_dir.exists() else None
    draft_options = DraftStructuringOptions(
        layouts_path=layouts,
        output_dir=output_dir,
        draft_filename=draft_filename,
        approved_filename=approved_filename,
        log_filename=log_filename,
        target_length=target_length,
        structure_pattern=structure_pattern,
        appendix_limit=appendix_limit,
        chapter_templates_dir=templates_dir,
        chapter_template_id=chapter_template,
        analysis_summary_path=analysis_summary_path,
    )

    context = _run_draft_pipeline(
        spec=spec,
        output_dir=output_dir,
        content_approved=content_approved,
        content_review_log=content_review_log,
        draft_options=draft_options,
    )

    meta_path = _write_draft_meta(
        context=context,
        output_dir=output_dir,
        meta_filename=meta_filename,
        draft_filename=draft_filename,
        approved_filename=approved_filename,
        log_filename=log_filename,
    )

    return context, meta_path, draft_options


def _echo_outline_outputs(
    *,
    output_dir: Path,
    draft_filename: str,
    approved_filename: str,
    log_filename: str,
    meta_path: Path,
) -> None:
    draft_path = output_dir / draft_filename
    approved_path = output_dir / approved_filename
    log_path = output_dir / log_filename

    click.echo(f"Outline Draft: {draft_path}")
    click.echo(f"Outline Approved: {approved_path}")
    click.echo(f"Outline Review Log: {log_path}")
    click.echo(f"Outline Meta: {meta_path}")


def _echo_outline_layout_details(context: PipelineContext) -> None:
    draft_document = context.artifacts.get("draft_document")
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


def _run_mapping_pipeline(
    *,
    spec: JobSpec,
    output_dir: Path,
    rules_config: RulesConfig,
    refiner_options: RefinerOptions,
    branding_artifact: dict[str, object],
    content_approved: Optional[Path],
    content_review_log: Optional[Path],
    layouts: Optional[Path],
    draft_output: Path,
    template: Optional[Path],
    draft_options: DraftStructuringOptions | None = None,
) -> PipelineContext:
    output_dir.mkdir(parents=True, exist_ok=True)
    draft_output.mkdir(parents=True, exist_ok=True)

    context = PipelineContext(spec=spec, workdir=output_dir)
    context.add_artifact("branding", branding_artifact)

    content_step = ContentApprovalStep(
        ContentApprovalOptions(
            approved_path=content_approved,
            review_log_path=content_review_log,
            require_document=False,
            require_all_approved=True,
        )
    )
    effective_draft_options = draft_options
    if effective_draft_options is not None:
        effective_draft_options = replace(
            effective_draft_options,
            output_dir=draft_output,
            layouts_path=effective_draft_options.layouts_path or layouts,
        )
    else:
        effective_draft_options = DraftStructuringOptions(
            layouts_path=layouts,
            output_dir=draft_output,
        )

    draft_step = DraftStructuringStep(effective_draft_options)
    spec_validator = SpecValidatorStep(
        max_title_length=rules_config.max_title_length,
        max_bullet_length=rules_config.max_bullet_length,
        max_bullet_level=rules_config.max_bullet_level,
        forbidden_words=rules_config.forbidden_words,
    )
    refiner = SimpleRefinerStep(refiner_options)
    mapping = MappingStep(
        MappingOptions(
            layouts_path=layouts,
            output_dir=output_dir,
            template_path=template,
        )
    )

    steps = [
        content_step,
        spec_validator,
        draft_step,
        refiner,
        mapping,
    ]
    PipelineRunner(steps).execute(context)
    return context


def _execute_mapping(
    *,
    spec: JobSpec,
    output_dir: Path,
    rules: Path,
    content_approved: Optional[Path],
    content_review_log: Optional[Path],
    layouts: Optional[Path],
    draft_output: Path,
    template: Optional[Path],
    branding: Optional[Path],
    draft_options: DraftStructuringOptions | None = None,
) -> PipelineContext:
    rules_config = RulesConfig.load(rules)
    branding_config, branding_artifact = _prepare_branding(template, branding)
    refiner_options = _build_refiner_options(rules_config, branding_config)

    return _run_mapping_pipeline(
        spec=spec,
        output_dir=output_dir,
        rules_config=rules_config,
        refiner_options=refiner_options,
        branding_artifact=branding_artifact,
        content_approved=content_approved,
        content_review_log=content_review_log,
        layouts=layouts,
        draft_output=draft_output,
        template=template,
        draft_options=draft_options,
    )


def _run_render_pipeline(
    *,
    generate_ready: GenerateReadyDocument,
    generate_ready_path: Optional[Path],
    output_dir: Path,
    template: Optional[Path],
    pptx_name: str,
    branding_config: BrandingConfig,
    branding_artifact: dict[str, object],
    analyzer_options: AnalyzerOptions,
    pdf_options: PdfExportOptions,
    polisher_options: PolisherOptions | None = None,
    base_artifacts: dict[str, object] | None = None,
) -> PipelineContext:
    output_dir.mkdir(parents=True, exist_ok=True)

    render_spec = generate_ready_to_jobspec(generate_ready)
    artifacts = dict(base_artifacts or {})

    context = PipelineContext(
        spec=render_spec,
        workdir=output_dir,
        artifacts=artifacts,
    )
    context.add_artifact("branding", branding_artifact)
    context.add_artifact("generate_ready", generate_ready)
    if generate_ready_path is not None:
        context.add_artifact("generate_ready_path", str(generate_ready_path))

    renderer = SimpleRendererStep(
        RenderingOptions(
            template_path=template,
            output_filename=pptx_name,
            branding=branding_config,
        )
    )
    baseline_analyzer_options = replace(
        analyzer_options,
        output_filename="analysis_pre_polisher.json",
        snapshot_output_filename=None,
    )
    baseline_analyzer = SimpleAnalyzerStep(
        baseline_analyzer_options,
        artifact_key="analysis_pre_polisher_path",
        register_default_artifact=False,
        allow_missing_artifact=True,
    )
    analyzer = SimpleAnalyzerStep(analyzer_options)

    polisher_step = PolisherStep(polisher_options or PolisherOptions())
    audit_step = RenderingAuditStep(RenderingAuditOptions())

    monitoring_step = MonitoringIntegrationStep(MonitoringIntegrationOptions())

    steps: list[PipelineStep] = [
        renderer,
        baseline_analyzer,
        polisher_step,
        audit_step,
    ]
    if pdf_options.enabled:
        steps.append(PdfExportStep(pdf_options))
    steps.extend([analyzer, monitoring_step])

    PipelineRunner(steps).execute(context)
    return context


def _echo_mapping_outputs(context: PipelineContext) -> None:
    draft_path = context.artifacts.get("draft_document_path")
    if draft_path is not None:
        click.echo(f"Draft: {draft_path}")
    draft_log_path = context.artifacts.get("draft_review_log_path")
    if draft_log_path is not None:
        click.echo(f"Draft Log: {draft_log_path}")
    generate_ready_path = context.artifacts.get("generate_ready_path")
    if generate_ready_path is not None:
        click.echo(f"Generate Ready: {generate_ready_path}")
    mapping_log_path = context.artifacts.get("mapping_log_path")
    if mapping_log_path is not None:
        click.echo(f"Mapping Log: {mapping_log_path}")
    fallback_report_path = context.artifacts.get("mapping_fallback_report_path")
    if fallback_report_path is not None:
        click.echo(f"Fallback Report: {fallback_report_path}")


def _echo_render_outputs(context: PipelineContext, audit_path: Path | None) -> None:
    pptx_path = context.artifacts.get("pptx_path")
    if pptx_path is not None:
        click.echo(f"PPTX: {pptx_path}")
    else:
        click.echo("PPTX: --pdf-mode=only のため保存しませんでした")
    analysis_path = context.artifacts.get("analysis_path")
    click.echo(f"Analysis: {analysis_path}")
    baseline_analysis_path = context.artifacts.get("analysis_pre_polisher_path")
    if baseline_analysis_path is not None:
        click.echo(f"Analysis (Pre-Polisher): {baseline_analysis_path}")
    rendering_log_path = context.artifacts.get("rendering_log_path")
    if rendering_log_path is not None:
        click.echo(f"Rendering Log: {rendering_log_path}")
    rendering_summary = context.artifacts.get("rendering_summary")
    if isinstance(rendering_summary, dict):
        click.echo(
            "Rendering Warnings: %s" % rendering_summary.get("warnings_total", 0)
        )
    review_engine_path = context.artifacts.get("review_engine_analysis_path")
    if review_engine_path is not None:
        click.echo(f"ReviewEngine Analysis: {review_engine_path}")
    snapshot_path = context.artifacts.get("analyzer_snapshot_path")
    if snapshot_path is not None:
        click.echo(f"Analyzer Snapshot: {snapshot_path}")
    pdf_path = context.artifacts.get("pdf_path")
    if pdf_path is not None:
        click.echo(f"PDF: {pdf_path}")
    polisher_meta = context.artifacts.get("polisher_metadata")
    if isinstance(polisher_meta, dict):
        status = polisher_meta.get("status", "unknown")
        click.echo(f"Polisher: {status}")
        summary = polisher_meta.get("summary")
        if isinstance(summary, dict) and summary:
            click.echo(
                "Polisher Summary: "
                + json.dumps(summary, ensure_ascii=False, sort_keys=True)
            )
    draft_path = context.artifacts.get("draft_document_path")
    if draft_path is not None:
        click.echo(f"Draft: {draft_path}")
    draft_log_path = context.artifacts.get("draft_review_log_path")
    if draft_log_path is not None:
        click.echo(f"Draft Log: {draft_log_path}")
    generate_ready_path = context.artifacts.get("generate_ready_path")
    if generate_ready_path is not None:
        click.echo(f"Generate Ready: {generate_ready_path}")
    mapping_log_path = context.artifacts.get("mapping_log_path")
    if mapping_log_path is not None:
        click.echo(f"Mapping Log: {mapping_log_path}")
    fallback_report_path = context.artifacts.get("mapping_fallback_report_path")
    if fallback_report_path is not None:
        click.echo(f"Fallback Report: {fallback_report_path}")
    monitoring_report_path = context.artifacts.get("monitoring_report_path")
    if monitoring_report_path is not None:
        click.echo(f"Monitoring Report: {monitoring_report_path}")
    if audit_path is not None:
        click.echo(f"Audit: {audit_path}")


@app.command("gen")
@click.argument(
    "generate_ready_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
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
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=DEFAULT_RULES_PATH,
    show_default=True,
    help="検証ルール設定ファイル",
)
@click.option(
    "--branding",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    show_default=str(DEFAULT_BRANDING_PATH),
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
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
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
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="Open XML Polisher (.exe / .dll) もしくはラッパースクリプトのパス",
)
@click.option(
    "--polisher-rules",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
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
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=None,
    help="Polisher 実行時のカレントディレクトリを固定する",
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
    branding: Optional[Path],
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
            "generate_ready.json に template_path が含まれていません。工程4を最新仕様で再実行するか、テンプレート情報を埋め込んでください。",
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
    branding_config, branding_artifact = _prepare_branding(template_path, branding)
    analyzer_options = _build_analyzer_options(
        rules_config, branding_config, emit_structure_snapshot
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

    base_artifacts: dict[str, object] = {
        "generate_ready": generate_ready,
        "generate_ready_path": str(generate_ready_path),
    }
    mapping_log_path = generate_ready_path.with_name("mapping_log.json")
    if mapping_log_path.exists():
        base_artifacts["mapping_log_path"] = str(mapping_log_path)
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
            branding_config=branding_config,
            branding_artifact=branding_artifact,
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


@app.command("content")
@click.argument(
    "spec_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
)
@click.option(
    "--content-approved",
    "content_approved_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    required=False,
    help="工程3で承認済みのコンテンツ JSON",
)
@click.option(
    "--content-review-log",
    "content_review_log_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="工程3の承認イベントログ JSON",
)
@click.option(
    "--output",
    "-o",
    "output_dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".pptx/content"),
    show_default=True,
    help="承認成果物を保存するディレクトリ",
)
@click.option(
    "--spec-output",
    type=str,
    default="spec_content_applied.json",
    show_default=True,
    help="承認内容を適用した Spec の出力ファイル名",
)
@click.option(
    "--normalized-content",
    type=str,
    default="content_approved.json",
    show_default=True,
    help="正規化した承認済みコンテンツの出力ファイル名",
)
@click.option(
    "--review-output",
    type=str,
    default="content_review_log.json",
    show_default=True,
    help="承認イベントログの正規化ファイル名",
)
@click.option(
    "--meta-filename",
    type=str,
    default="content_meta.json",
    show_default=True,
    help="承認メタ情報の出力ファイル名",
)
@click.option(
    "--content-source",
    "content_sources",
    multiple=True,
    type=str,
    help="プレーンテキスト / PDF / URL からドラフトを生成する入力ソース",
)
@click.option(
    "--ai-policy",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="生成AI用のポリシー定義 JSON。未指定時は config/content_ai_policies.json を利用する。",
)
@click.option(
    "--ai-policy-id",
    type=str,
    default=None,
    help="使用するポリシー ID。未指定時は定義ファイルの default_policy_id を利用する。",
)
@click.option(
    "--ai-output",
    type=str,
    default="content_ai_log.json",
    show_default=True,
    help="AI 生成ログの出力ファイル名。",
)
@click.option(
    "--ai-meta",
    type=str,
    default="ai_generation_meta.json",
    show_default=True,
    help="AI 生成メタ情報の出力ファイル名。",
)
@click.option(
    "--draft-output",
    type=str,
    default="content_draft.json",
    show_default=True,
    help="--content-source 利用時に生成するドラフトファイル名",
)
@click.option(
    "--import-meta",
    "import_meta_filename",
    type=str,
    default="content_import_meta.json",
    show_default=True,
    help="--content-source 利用時に生成するメタ情報ファイル名",
)
@click.option(
    "--libreoffice-path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="PDF 取り込み時に利用する LibreOffice 実行ファイルのパス",
)
@click.option(
    "--slide-count",
    type=click.IntRange(1, None),
    default=None,
    help="生成するスライド枚数。未指定時は LLM の判断（mock の場合は 5 枚固定）",
)
def content(
    spec_path: Path,
    content_approved_path: Path | None,
    content_review_log_path: Path | None,
    output_dir: Path,
    spec_output: str,
    normalized_content: str,
    review_output: str,
    meta_filename: str,
    content_sources: tuple[str, ...],
    ai_policy: Path | None,
    ai_policy_id: str | None,
    ai_output: str,
    ai_meta: str,
    draft_output: str,
    import_meta_filename: str,
    libreoffice_path: Path | None,
    slide_count: int | None,
) -> None:
    """工程3 コンテンツ正規化: 承認済みコンテンツを検証し Spec へ適用する。"""

    try:
        spec = _load_jobspec(spec_path)
    except SpecValidationError as exc:
        _echo_errors("スキーマ検証に失敗しました", exc.errors)
        raise click.exceptions.Exit(code=2) from exc

    if content_sources and content_approved_path is not None:
        click.echo("--content-source と --content-approved を同時には指定できません", err=True)
        raise click.exceptions.Exit(code=2)

    import_reference_text: str | None = None
    import_meta_path: Path | None = None
    import_warnings: list[str] = []

    if content_sources:
        output_dir.mkdir(parents=True, exist_ok=True)
        importer = ContentImportService(libreoffice_path=libreoffice_path)
        try:
            result = importer.import_sources(content_sources)
        except ContentImportError as exc:
            click.echo(f"コンテンツ取り込みに失敗しました: {exc}", err=True)
            raise click.exceptions.Exit(code=4) from exc

        import_reference_text, _ = _build_reference_text(result.document)
        import_warnings.extend(result.warnings)

        meta_payload = {
            **result.meta,
            "spec": {
                "slides": len(spec.slides),
                "source": str(spec_path.resolve()),
            },
        }
        import_meta_path = output_dir / import_meta_filename
        _dump_json(import_meta_path, meta_payload)

    if content_approved_path is not None:
        try:
            context = _run_content_approval_pipeline(
                spec=spec,
                output_dir=output_dir,
                content_approved=content_approved_path,
                content_review_log=content_review_log_path,
                require_document=True,
            )
        except ContentApprovalError as exc:
            click.echo(f"承認済みコンテンツの読み込みに失敗しました: {exc}", err=True)
            raise click.exceptions.Exit(code=4) from exc
        except FileNotFoundError as exc:
            click.echo(f"ファイルが見つかりません: {exc}", err=True)
            raise click.exceptions.Exit(code=4) from exc
        except Exception as exc:  # noqa: BLE001
            logging.exception("content 実行中にエラーが発生しました")
            raise click.exceptions.Exit(code=1) from exc

        spec_output_path, content_output_path, review_output_path, meta_path = _write_content_outputs(
            context=context,
            output_dir=output_dir,
            spec_filename=spec_output,
            content_filename=normalized_content,
            review_filename=review_output,
            meta_filename=meta_filename,
        )

        click.echo(f"Spec (content applied): {spec_output_path}")
        if content_output_path is not None:
            click.echo(f"Content Approved (normalized): {content_output_path}")
        if review_output_path is not None:
            click.echo(f"Content Review Log (normalized): {review_output_path}")
        click.echo(f"Content Meta: {meta_path}")
        return

    policy_path = ai_policy or DEFAULT_AI_POLICY_PATH
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        policy_set = load_policy_set(policy_path)
    except ContentAIPolicyError as exc:
        click.echo(f"AI ポリシー定義の読み込みに失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc

    try:
        llm_client = create_llm_client()
    except LLMClientConfigurationError as exc:
        click.echo(f"AI クライアントの初期化に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc

    target_slide_count = slide_count
    if target_slide_count is None and isinstance(llm_client, MockLLMClient):
        target_slide_count = 5

    available_slides = len(spec.slides)
    if target_slide_count is not None and target_slide_count > available_slides:
        import_warnings.append(
            f"テンプレートには {available_slides} 枚しか含まれないため、生成枚数を {available_slides} 枚に調整します"
        )

    try:
        orchestrator = ContentAIOrchestrator(policy_set, llm_client=llm_client)
    except LLMClientConfigurationError as exc:
        click.echo(f"AI クライアントの初期化に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    try:
        document, meta_payload, log_entries = orchestrator.generate_document(
            spec,
            policy_id=ai_policy_id,
            reference_text=import_reference_text,
            slide_limit=target_slide_count,
        )
    except ContentAIOrchestrationError as exc:
        msg = str(exc)
        if "token" in msg.lower():
            click.echo(
                "AI 生成に失敗しました: トークン上限に達した可能性があります。"
                " --content-source やポリシー設定で入力文量を調整してください。",
                err=True,
            )
        else:
            click.echo(f"AI 生成に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc

    draft_path = output_dir / draft_output
    ai_meta_path = output_dir / ai_meta
    log_path = output_dir / ai_output

    _dump_json(draft_path, document.model_dump(mode="json"))
    _dump_json(ai_meta_path, meta_payload)
    _dump_json(log_path, log_entries)

    if import_meta_path is not None:
        logger.info("Content Import Meta: %s", import_meta_path)
        click.echo(f"Content Import Meta: {import_meta_path}")
    for warning in import_warnings:
        logger.warning("%s", warning)
        click.echo(f"Warning: {warning}", err=True)

    logger.info("Content Draft (AI): %s", draft_path)
    click.echo(f"Content Draft (AI): {draft_path}")
    logger.info("AI Generation Meta: %s", ai_meta_path)
    click.echo(f"AI Generation Meta: {ai_meta_path}")
    logger.info("AI Generation Log: %s", log_path)
    click.echo(f"AI Generation Log: {log_path}")
    return


@app.command("outline")
@click.argument(
    "spec_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
)
@click.option(
    "--content-approved",
    "content_approved_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="工程3の承認済みコンテンツ JSON",
)
@click.option(
    "--content-review-log",
    "content_review_log_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="工程3の承認イベントログ JSON",
)
@click.option(
    "--layouts",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="工程2で生成した layouts.jsonl のパス",
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
    "--draft-filename",
    type=str,
    default="draft_draft.json",
    show_default=True,
    help="ドラフト案ファイル名",
)
@click.option(
    "--approved-filename",
    type=str,
    default="draft_approved.json",
    show_default=True,
    help="承認済みドラフトファイル名",
)
@click.option(
    "--log-filename",
    type=str,
    default="draft_review_log.json",
    show_default=True,
    help="ドラフトレビュー ログのファイル名",
)
@click.option(
    "--meta-filename",
    type=str,
    default="draft_meta.json",
    show_default=True,
    help="ドラフトメタ情報のファイル名",
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
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
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
def outline(
    spec_path: Path,
    content_approved_path: Path | None,
    content_review_log_path: Path | None,
    layouts: Path | None,
    output_dir: Path,
    draft_filename: str,
    approved_filename: str,
    log_filename: str,
    meta_filename: str,
    target_length: int | None,
    structure_pattern: str | None,
    appendix_limit: int,
    chapter_templates_dir: Path,
    chapter_template: str | None,
    analysis_summary_path: Path | None,
    return_reasons_path: Path,
    return_reasons: bool,
    show_layout_reasons: bool,
) -> None:
    """工程4 ドラフト構成（アウトライン）を生成する。"""

    if return_reasons:
        reasons = load_return_reasons(return_reasons_path)
        if not reasons:
            click.echo(f"差戻し理由テンプレートが見つかりません: {return_reasons_path}")
        else:
            click.echo("差戻し理由テンプレート一覧:")
            for reason in reasons:
                label = f"{reason.code} ({reason.severity})"
                if reason.label and reason.label != reason.code:
                    label += f" - {reason.label}"
                click.echo(f"- {label}")
        return

    try:
        spec = _load_jobspec(spec_path)
    except SpecValidationError as exc:
        _echo_errors("スキーマ検証に失敗しました", exc.errors)
        raise click.exceptions.Exit(code=2) from exc

    try:
        context, meta_path, _ = _execute_outline(
            spec=spec,
            output_dir=output_dir,
            content_approved=content_approved_path,
            content_review_log=content_review_log_path,
            layouts=layouts,
            draft_filename=draft_filename,
            approved_filename=approved_filename,
            log_filename=log_filename,
            meta_filename=meta_filename,
            target_length=target_length,
            structure_pattern=structure_pattern,
            appendix_limit=appendix_limit,
            chapter_templates_dir=chapter_templates_dir,
            chapter_template=chapter_template,
            analysis_summary_path=analysis_summary_path,
        )
    except ContentApprovalError as exc:
        click.echo(f"承認済みコンテンツの取り込みに失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except DraftStructuringError as exc:
        click.echo(f"ドラフト構成の生成に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except FileNotFoundError as exc:
        click.echo(f"ファイルが見つかりません: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("outline 実行中にエラーが発生しました")
        raise click.exceptions.Exit(code=1) from exc

    _echo_outline_outputs(
        output_dir=output_dir,
        draft_filename=draft_filename,
        approved_filename=approved_filename,
        log_filename=log_filename,
        meta_path=meta_path,
    )

    if show_layout_reasons:
        _echo_outline_layout_details(context)


@app.command("mapping")
@click.argument(
    "spec_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
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
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=DEFAULT_RULES_PATH,
    show_default=True,
    help="検証ルール設定ファイル",
)
@click.option(
    "--content-approved",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="工程3の承認済みコンテンツ JSON",
)
@click.option(
    "--content-review-log",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="工程3の承認イベントログ JSON",
)
@click.option(
    "--layouts",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="layouts.jsonl のパス",
)
@click.option(
    "--draft-output",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".pptx/draft"),
    show_default=True,
    help="draft_draft.json / draft_approved.json の出力先",
)
@click.option(
    "--template",
    "-t",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="ブランド抽出に利用するテンプレートファイル（任意）",
)
@click.option(
    "--branding",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    show_default=str(DEFAULT_BRANDING_PATH),
    help="ブランド設定ファイル（任意）",
)
def mapping(  # noqa: PLR0913
    spec_path: Path,
    output_dir: Path,
    rules: Path,
    content_approved: Optional[Path],
    content_review_log: Optional[Path],
    layouts: Optional[Path],
    draft_output: Path,
    template: Optional[Path],
    branding: Optional[Path],
) -> None:
    """工程5 マッピングを実行し generate_ready.json を生成する。"""
    try:
        spec = _load_jobspec(spec_path)
    except SpecValidationError as exc:
        _echo_errors("スキーマ検証に失敗しました", exc.errors)
        raise click.exceptions.Exit(code=2) from exc

    try:
        context = _execute_mapping(
            spec=spec,
            output_dir=output_dir,
            rules=rules,
            content_approved=content_approved,
            content_review_log=content_review_log,
            layouts=layouts,
            draft_output=draft_output,
            template=template,
            branding=branding,
        )
    except SpecValidationError as exc:
        _echo_errors("業務ルール検証に失敗しました", exc.errors)
        raise click.exceptions.Exit(code=3) from exc
    except ContentApprovalError as exc:
        click.echo(f"承認済みコンテンツの読み込みに失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("マッピング実行中にエラーが発生しました")
        raise click.exceptions.Exit(code=1) from exc

    _echo_mapping_outputs(context)


@app.command("compose")
@click.argument(
    "spec_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
)
@click.option(
    "--draft-output",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".pptx/draft"),
    show_default=True,
    help="工程4の成果物を保存するディレクトリ",
)
@click.option(
    "--output",
    "compose_output",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".pptx/gen"),
    show_default=True,
    help="工程5の成果物を保存するディレクトリ",
)
@click.option(
    "--content-approved",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="工程3の承認済みコンテンツ JSON",
)
@click.option(
    "--content-review-log",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="工程3の承認イベントログ JSON",
)
@click.option(
    "--layouts",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="工程2で生成した layouts.jsonl のパス",
)
@click.option(
    "--draft-filename",
    type=str,
    default="draft_draft.json",
    show_default=True,
    help="ドラフト案ファイル名",
)
@click.option(
    "--approved-filename",
    type=str,
    default="draft_approved.json",
    show_default=True,
    help="承認済みドラフトファイル名",
)
@click.option(
    "--draft-log-filename",
    type=str,
    default="draft_review_log.json",
    show_default=True,
    help="ドラフトレビュー ログのファイル名",
)
@click.option(
    "--draft-meta-filename",
    type=str,
    default="draft_meta.json",
    show_default=True,
    help="ドラフトメタ情報のファイル名",
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
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
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
    "--rules",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=DEFAULT_RULES_PATH,
    show_default=True,
    help="検証ルール設定ファイル",
)
@click.option(
    "--template",
    "compose_template",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="ブランド抽出に利用するテンプレートファイル（任意）",
)
@click.option(
    "--branding",
    "compose_branding",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    show_default=str(DEFAULT_BRANDING_PATH),
    help="ブランド設定ファイル（任意）",
)
def compose(  # noqa: PLR0913
    spec_path: Path,
    draft_output: Path,
    compose_output: Path,
    content_approved: Path | None,
    content_review_log: Path | None,
    layouts: Path | None,
    draft_filename: str,
    approved_filename: str,
    draft_log_filename: str,
    draft_meta_filename: str,
    target_length: int | None,
    structure_pattern: str | None,
    appendix_limit: int,
    chapter_templates_dir: Path,
    chapter_template: str | None,
    analysis_summary_path: Path | None,
    show_layout_reasons: bool,
    rules: Path,
    compose_template: Path | None,
    compose_branding: Path | None,
) -> None:
    """工程4（アウトライン）と工程5（マッピング）を連続実行する。"""

    try:
        spec = _load_jobspec(spec_path)
    except SpecValidationError as exc:
        _echo_errors("スキーマ検証に失敗しました", exc.errors)
        raise click.exceptions.Exit(code=2) from exc

    try:
        outline_context, outline_meta_path, draft_options = _execute_outline(
            spec=spec,
            output_dir=draft_output,
            content_approved=content_approved,
            content_review_log=content_review_log,
            layouts=layouts,
            draft_filename=draft_filename,
            approved_filename=approved_filename,
            log_filename=draft_log_filename,
            meta_filename=draft_meta_filename,
            target_length=target_length,
            structure_pattern=structure_pattern,
            appendix_limit=appendix_limit,
            chapter_templates_dir=chapter_templates_dir,
            chapter_template=chapter_template,
            analysis_summary_path=analysis_summary_path,
        )
    except ContentApprovalError as exc:
        click.echo(f"承認済みコンテンツの取り込みに失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except DraftStructuringError as exc:
        click.echo(f"ドラフト構成の生成に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except FileNotFoundError as exc:
        click.echo(f"ファイルが見つかりません: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("compose 実行中に工程4でエラーが発生しました")
        raise click.exceptions.Exit(code=1) from exc

    _echo_outline_outputs(
        output_dir=draft_output,
        draft_filename=draft_filename,
        approved_filename=approved_filename,
        log_filename=draft_log_filename,
        meta_path=outline_meta_path,
    )

    if show_layout_reasons:
        _echo_outline_layout_details(outline_context)

    try:
        mapping_context = _execute_mapping(
            spec=spec,
            output_dir=compose_output,
            rules=rules,
            content_approved=content_approved,
            content_review_log=content_review_log,
            layouts=layouts,
            draft_output=draft_output,
            template=compose_template,
            branding=compose_branding,
            draft_options=draft_options,
        )
    except SpecValidationError as exc:
        _echo_errors("業務ルール検証に失敗しました", exc.errors)
        raise click.exceptions.Exit(code=3) from exc
    except ContentApprovalError as exc:
        click.echo(f"承認済みコンテンツの読み込みに失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("compose 実行中に工程5でエラーが発生しました")
        raise click.exceptions.Exit(code=1) from exc

    _echo_mapping_outputs(mapping_context)


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
    "--output",
    "-o",
    "output_dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path(".pptx/extract"),
    show_default=True,
    help="テンプレート仕様とブランド設定を保存するディレクトリ",
)
def tpl_extract(
    template_path: Path,
    output_dir: Path,
    layout: Optional[str],
    anchor: Optional[str],
    format: str,
) -> None:
    """テンプレートファイルから図形・プレースホルダー情報を抽出してJSON仕様の雛形を生成する。"""
    try:
        # オプション設定
        extractor_options = TemplateExtractorOptions(
            template_path=template_path,
            output_path=None,
            layout_filter=layout,
            anchor_filter=anchor,
            format=format.lower(),
        )
        
        # 出力ディレクトリ作成
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 抽出実行
        extractor = TemplateExtractor(extractor_options)
        template_spec = extractor.extract()
        jobspec_scaffold = extractor.build_jobspec_scaffold(template_spec)
        branding_result = extract_branding_config(template_path)
        
        # 出力パス決定
        if format.lower() == "yaml":
            spec_path = output_dir / "template_spec.yaml"
        else:
            spec_path = output_dir / "template_spec.json"
        branding_output_path = output_dir / "branding.json"
        jobspec_output_path = spec_path.with_name("jobspec.json")
        
        # ファイル保存
        if format.lower() == "yaml":
            import yaml
            content = yaml.dump(
                template_spec.model_dump(),
                allow_unicode=True,
                default_flow_style=False,
                indent=2
            )
        else:
            import json
            content = json.dumps(
                template_spec.model_dump(),
                indent=2,
                ensure_ascii=False
            )
        
        spec_path.write_text(content, encoding="utf-8")
        logger.info("Saved template spec to %s", spec_path.resolve())

        branding_payload = branding_result.to_branding_payload()
        branding_text = json.dumps(branding_payload, ensure_ascii=False, indent=2)
        branding_output_path.write_text(branding_text, encoding="utf-8")
        logger.info("Saved branding payload to %s", branding_output_path.resolve())

        extractor.save_jobspec_scaffold(jobspec_scaffold, jobspec_output_path)
        logger.info("Saved jobspec scaffold to %s", jobspec_output_path.resolve())

        # 結果表示
        click.echo(f"テンプレート抽出が完了しました: {spec_path}")
        click.echo(f"ブランド設定を出力しました: {branding_output_path}")
        click.echo(f"ジョブスペック雛形を出力しました: {jobspec_output_path}")
        click.echo(f"抽出されたレイアウト数: {len(template_spec.layouts)}")

        total_anchors = sum(len(layout.anchors) for layout in template_spec.layouts)
        click.echo(f"抽出された図形・アンカー数: {total_anchors}")

        click.echo(f"ジョブスペックのスライド数: {len(jobspec_scaffold.slides)}")

        logger.info("Starting layout validation for %s", template_path)
        validation_options = LayoutValidationOptions(
            template_path=template_path,
            output_dir=output_dir,
        )
        validation_suite = LayoutValidationSuite(validation_options)
        validation_result = validation_suite.run()
        logger.info(
            "Layout validation finished: warnings=%d errors=%d",
            validation_result.warnings_count,
            validation_result.errors_count,
        )

        click.echo(f"Layouts: {validation_result.layouts_path}")
        click.echo(f"Diagnostics: {validation_result.diagnostics_path}")
        if validation_result.diff_report_path is not None:
            click.echo(f"Diff: {validation_result.diff_report_path}")
        click.echo(
            "検出結果: warnings=%d, errors=%d"
            % (validation_result.warnings_count, validation_result.errors_count)
        )

        if template_spec.warnings:
            click.echo(f"警告: {len(template_spec.warnings)} 件")
            for warning in template_spec.warnings:
                click.echo(f"  - {warning}", err=True)
        
        if template_spec.errors:
            click.echo(f"エラー: {len(template_spec.errors)} 件")
            for error in template_spec.errors:
                click.echo(f"  - {error}", err=True)
        
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


@app.command("layout-validate")
@click.option(
    "--template",
    "-t",
    "template_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
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
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="比較対象となる過去の layouts.jsonl",
)
@click.option(
    "--analyzer-snapshot",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
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
        "検出結果: warnings=%d, errors=%d" % (result.warnings_count, result.errors_count)
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
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    default=None,
    help="比較対象となる過去の template_release.json",
)
@click.option(
    "--golden-spec",
    "golden_specs",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    multiple=True,
    help="テンプレ互換性検証に使用する spec ファイル（複数指定可）",
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
) -> None:
    """テンプレート受け渡しメタと差分レポートを生成する。"""

    try:
        resolved_template_id = _resolve_template_id(template_id, brand, version)

        extractor = TemplateExtractor(TemplateExtractorOptions(template_path=template_path))
        spec = extractor.extract()

        output_dir.mkdir(parents=True, exist_ok=True)

        baseline = None
        if baseline_release is not None:
            baseline = load_template_release(baseline_release)

        resolved_golden_specs, auto_golden_warnings = _resolve_golden_specs(
            user_specs=list(golden_specs),
            baseline=baseline,
            baseline_release=baseline_release,
        )

        golden_runs: list[TemplateReleaseGoldenRun] = []
        golden_warnings: list[str] = []
        golden_errors: list[str] = []
        if resolved_golden_specs:
            golden_runs, golden_warnings, golden_errors = _run_golden_specs(
                template_path=template_path,
                golden_specs=resolved_golden_specs,
                output_dir=output_dir,
            )

        combined_warnings = golden_warnings + auto_golden_warnings

        release = build_template_release(
            template_path=template_path,
            spec=spec,
            template_id=resolved_template_id,
            brand=brand,
            version=version,
            generated_by=generated_by,
            reviewed_by=reviewed_by,
            golden_runs=golden_runs,
            extra_warnings=combined_warnings,
            extra_errors=golden_errors,
        )
        release_path = output_dir / "template_release.json"
        release_path.write_text(
            json.dumps(release.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Saved template release to %s", release_path.resolve())

        if golden_runs:
            golden_runs_path = output_dir / "golden_runs.json"
            golden_runs_path.write_text(
                json.dumps(
                    [run.model_dump() for run in golden_runs],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            logger.info("Saved golden run log to %s", golden_runs_path.resolve())

        report = build_release_report(current=release, baseline=baseline)
        report_path = output_dir / "release_report.json"
        report_path.write_text(
            json.dumps(report.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Saved release report to %s", report_path.resolve())

        click.echo(f"テンプレートリリースメタを出力しました: {release_path}")
        click.echo(f"差分レポートを出力しました: {report_path}")
        if golden_runs:
            click.echo(f"ゴールデンサンプル結果を出力しました: {golden_runs_path}")
        if baseline_release is not None:
            click.echo(f"比較対象: {baseline_release}")

        _print_diagnostics(release.diagnostics)

        if release.diagnostics.errors:
            raise click.exceptions.Exit(code=6)

    except click.exceptions.Exit:
        raise
    except FileNotFoundError as exc:
        click.echo(f"ファイルが見つかりません: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("テンプレートリリース生成中にエラーが発生しました")
        click.echo(f"テンプレートリリースの生成に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=1) from exc


def _run_golden_specs(
    *, template_path: Path, golden_specs: list[Path], output_dir: Path
) -> tuple[list[TemplateReleaseGoldenRun], list[str], list[str]]:
    results: list[TemplateReleaseGoldenRun] = []
    warnings: list[str] = []
    errors: list[str] = []

    if not golden_specs:
        return results, warnings, errors

    rules_config = RulesConfig.load(DEFAULT_RULES_PATH)
    branding_config = _load_branding_for_template(template_path, warnings)

    golden_root = output_dir / "golden_runs"

    for spec_path in golden_specs:
        run_dir = golden_root / spec_path.stem
        result = TemplateReleaseGoldenRun(
            spec_path=str(spec_path),
            status="passed",
            output_dir=str(run_dir),
        )

        try:
            spec = _load_jobspec(spec_path)
        except SpecValidationError as exc:
            detail = json.dumps(exc.errors, ensure_ascii=False)
            message = (
                f"golden spec {spec_path} のスキーマ検証に失敗しました"
            )
            result.status = "failed"
            result.errors.extend([message, detail])
            errors.append(message)
            results.append(result)
            continue
        except Exception as exc:  # noqa: BLE001
            message = f"golden spec {spec_path} の読み込みに失敗しました: {exc}"
            result.status = "failed"
            result.errors.append(message)
            errors.append(message)
            results.append(result)
            continue

        run_dir.mkdir(parents=True, exist_ok=True)
        context = PipelineContext(spec=spec, workdir=run_dir)

        renderer = SimpleRendererStep(
            RenderingOptions(
                template_path=template_path,
                output_filename=f"{spec_path.stem}.pptx",
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
                large_text_threshold_pt=branding_config.body_font.size_pt,
            )
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
        runner = PipelineRunner(steps)

        try:
            runner.execute(context)
        except SpecValidationError as exc:
            detail = json.dumps(exc.errors, ensure_ascii=False)
            message = (
                f"golden spec {spec_path} の業務ルール検証に失敗しました"
            )
            result.status = "failed"
            result.errors.extend([message, detail])
            errors.append(message)
        except Exception as exc:  # noqa: BLE001
            logging.exception(
                "ゴールデンサンプル実行中にエラーが発生しました: %s", spec_path
            )
            message = f"golden spec {spec_path} の実行に失敗しました: {exc}"
            result.status = "failed"
            result.errors.append(message)
            errors.append(message)
        else:
            pptx_path = context.artifacts.get("pptx_path")
            if pptx_path is not None:
                result.pptx_path = str(pptx_path)
            analysis_path = context.artifacts.get("analysis_path")
            if analysis_path is not None:
                result.analysis_path = str(analysis_path)
            pdf_path = context.artifacts.get("pdf_path")
            if pdf_path is not None:
                result.pdf_path = str(pdf_path)

            analyzer_warnings = context.artifacts.get("analyzer_warnings")
            if isinstance(analyzer_warnings, list):
                new_warnings = [str(item) for item in analyzer_warnings]
                result.warnings.extend(new_warnings)
                for warning in new_warnings:
                    warnings.append(f"golden spec {spec_path}: {warning}")

        results.append(result)

    return results, warnings, errors


def _resolve_golden_specs(
    *,
    user_specs: list[Path],
    baseline: TemplateRelease | None,
    baseline_release: Path | None,
) -> tuple[list[Path], list[str]]:
    resolved: list[Path] = []
    warnings: list[str] = []
    seen: set[Path] = set()

    def _add_spec(path: Path) -> None:
        try:
            normalized = path.resolve()
        except OSError:
            normalized = path
        if normalized in seen:
            return
        resolved.append(path)
        seen.add(normalized)

    for spec in user_specs:
        _add_spec(spec)

    if baseline is None:
        return resolved, warnings

    if user_specs:
        return resolved, warnings

    base_dir = baseline_release.parent if baseline_release is not None else Path.cwd()
    for run in baseline.golden_runs:
        candidate = _resolve_golden_spec_path(run.spec_path, base_dir)
        if candidate is None:
            warnings.append(
                f"baseline のゴールデンスペックを解決できませんでした: {run.spec_path}"
            )
            continue
        _add_spec(candidate)

    return resolved, warnings


def _resolve_golden_spec_path(spec_path: str, base_dir: Path) -> Path | None:
    candidate = Path(spec_path)
    if candidate.is_absolute() and candidate.exists():
        return candidate

    cwd_candidate = Path.cwd() / candidate
    if cwd_candidate.exists():
        return cwd_candidate

    fallback = base_dir / candidate
    if fallback.exists():
        return fallback

    return None


def _load_branding_for_template(
    template_path: Path, warnings: list[str]
) -> BrandingConfig:
    try:
        extraction = extract_branding_config(template_path)
    except BrandingExtractionError as exc:
        warnings.append(
            f"テンプレートからブランド設定を抽出できなかったためデフォルト設定を使用します: {exc}"
        )
        try:
            return BrandingConfig.load(DEFAULT_BRANDING_PATH)
        except FileNotFoundError:
            warnings.append(
                f"デフォルトのブランド設定が見つからないため内蔵設定を使用します: {DEFAULT_BRANDING_PATH}"
            )
            return BrandingConfig.default()
    else:
        return extraction.to_branding_config()


def _resolve_template_id(
    template_id: Optional[str], brand: str, version: str
) -> str:
    if template_id and template_id.strip():
        return template_id.strip()
    base = f"{brand}_{version}"
    return base.replace(" ", "_")


def _print_diagnostics(diagnostics: TemplateReleaseDiagnostics) -> None:
    if diagnostics.warnings:
        click.echo(f"警告: {len(diagnostics.warnings)} 件", err=True)
        for warning in diagnostics.warnings:
            click.echo(f"  - {warning}", err=True)
    if diagnostics.errors:
        click.echo(f"エラー: {len(diagnostics.errors)} 件", err=True)
        for error in diagnostics.errors:
            click.echo(f"  - {error}", err=True)


def _echo_errors(message: str, errors: list[dict[str, object]] | None) -> None:
    click.echo(message, err=True)
    if not errors:
        return
    formatted = json.dumps(errors, ensure_ascii=False, indent=2)
    click.echo(formatted, err=True)


def _emit_review_engine_analysis(
    context: PipelineContext, analysis_path: object | None
) -> Path | None:
    if analysis_path is None:
        return None

    path = Path(str(analysis_path))
    if not path.exists():
        logger.warning(
            "Review Engine 連携ファイル生成のため analysis.json が見つかりません: %s", path
        )
        return None

    adapter = AnalyzerReviewEngineAdapter()
    try:
        logger.info("Loading analysis payload from %s", path.resolve())
        analysis_payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "analysis.json の読み込みに失敗したため Review Engine 連携ファイルを生成しません: %s",
            exc,
        )
        return None

    try:
        payload = adapter.build_payload(analysis_payload, context.spec)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Review Engine 連携ペイロードの生成に失敗しました: %s",
            exc,
        )
        return None

    output_path = path.with_name("review_engine_analyzer.json")
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Saved review engine payload to %s", output_path.resolve())
    context.add_artifact("review_engine_analysis_path", output_path)
    return output_path


def _write_audit_log(context: PipelineContext) -> Path:
    outputs_dir = context.workdir
    outputs_dir.mkdir(parents=True, exist_ok=True)
    artifacts_payload = {
        "pptx": _artifact_str(context.artifacts.get("pptx_path")),
        "analysis": _artifact_str(context.artifacts.get("analysis_path")),
        "analysis_pre_polisher": _artifact_str(
            context.artifacts.get("analysis_pre_polisher_path")
        ),
        "review_engine_analysis": _artifact_str(
            context.artifacts.get("review_engine_analysis_path")
        ),
        "pdf": _artifact_str(context.artifacts.get("pdf_path")),
        "generate_ready": _artifact_str(
            context.artifacts.get("generate_ready_path")
        ),
        "rendering_log": _artifact_str(
            context.artifacts.get("rendering_log_path")
        ),
        "mapping_log": _artifact_str(context.artifacts.get("mapping_log_path")),
        "mapping_fallback_report": _artifact_str(
            context.artifacts.get("mapping_fallback_report_path")
        ),
        "monitoring_report": _artifact_str(
            context.artifacts.get("monitoring_report_path")
        ),
    }

    pdf_meta = context.artifacts.get("pdf_export_metadata")
    if isinstance(pdf_meta, dict):
        pdf_payload = {
            "enabled": True,
            "status": pdf_meta.get("status", "success"),
            "attempts": pdf_meta.get("attempts", 0),
            "elapsed_ms": int(pdf_meta.get("elapsed_sec", 0.0) * 1000),
            "converter": pdf_meta.get("converter"),
        }
    else:
        pdf_payload = None

    polisher_meta = context.artifacts.get("polisher_metadata")
    if isinstance(polisher_meta, dict):
        polisher_payload = {
            "enabled": bool(polisher_meta.get("enabled")),
            "status": polisher_meta.get("status"),
            "elapsed_ms": int(polisher_meta.get("elapsed_sec", 0.0) * 1000)
            if polisher_meta.get("elapsed_sec") is not None
            else None,
            "rules_path": polisher_meta.get("rules_path"),
            "summary": polisher_meta.get("summary"),
        }
    else:
        polisher_payload = None

    hashes: dict[str, str] = {}
    for label, key in (
        ("generate_ready", "generate_ready_path"),
        ("pptx", "pptx_path"),
        ("analysis", "analysis_path"),
        ("analysis_pre_polisher", "analysis_pre_polisher_path"),
        ("pdf", "pdf_path"),
        ("rendering_log", "rendering_log_path"),
        ("monitoring_report", "monitoring_report_path"),
        ("mapping_log", "mapping_log_path"),
        ("mapping_fallback_report", "mapping_fallback_report_path"),
    ):
        digest = _sha256_of(context.artifacts.get(key))
        if digest:
            hashes[label] = digest

    audit_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec_meta": context.spec.meta.model_dump(),
        "slides": len(context.spec.slides),
        "artifacts": artifacts_payload,
        "rendering": context.artifacts.get("rendering_summary"),
        "pdf_export": pdf_payload,
        "refiner_adjustments": context.artifacts.get("refiner_adjustments"),
        "branding": context.artifacts.get("branding"),
        "polisher": polisher_payload,
    }
    monitoring_summary = context.artifacts.get("monitoring_summary")
    if monitoring_summary is not None:
        audit_payload["monitoring"] = monitoring_summary
    if hashes:
        audit_payload["hashes"] = hashes
    content_meta = context.artifacts.get("content_approved_meta")
    if content_meta is not None:
        audit_payload["content_approval"] = content_meta
    review_meta = context.artifacts.get("content_review_log_meta")
    if review_meta is not None:
        audit_payload["content_review_log"] = review_meta
    mapping_meta = context.artifacts.get("mapping_meta")
    if mapping_meta is not None:
        audit_payload["mapping"] = mapping_meta
    audit_path = outputs_dir / "audit_log.json"
    audit_path.write_text(json.dumps(
        audit_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved audit log to %s", audit_path.resolve())
    context.add_artifact("audit_path", audit_path)
    return audit_path


def _artifact_str(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _sha256_of(value: object | None) -> str | None:
    if value is None:
        return None
    path = Path(str(value))
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            if not chunk:
                break
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


if __name__ == "__main__":
    app()
