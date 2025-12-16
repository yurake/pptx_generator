from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click

from pptx_generator.generate_ready import generate_ready_to_jobspec
from pptx_generator.models import GenerateReadyDocument, TemplateStyle
from pptx_generator.pipeline import (
    AnalyzerOptions,
    MonitoringIntegrationOptions,
    MonitoringIntegrationStep,
    PdfExportError,
    PdfExportOptions,
    PdfExportStep,
    PipelineContext,
    PipelineRunner,
    PolisherError,
    PolisherOptions,
    PolisherStep,
    RenderingOptions,
    RenderingAuditOptions,
    RenderingAuditStep,
    SimpleAnalyzerStep,
    SimpleRendererStep,
)
from pptx_generator.review_engine import AnalyzerReviewEngineAdapter
from pptx_generator.settings import RulesConfig
from pptx_generator.settings.loader import load_rules_config
from pptx_generator.settings.paths import find_config_path
from pptx_generator.template_style import extract_template_style

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class GenerateCommandConfig:
    generate_ready_path: Path
    output_dir: Path
    pptx_name: str
    rules_path: Path
    export_pdf: bool
    pdf_mode: str
    pdf_output: str
    libreoffice_path: Optional[Path]
    pdf_timeout: int
    pdf_retries: int
    polisher_toggle: bool | None
    polisher_path: Optional[Path]
    polisher_rules: Optional[Path]
    polisher_timeout: Optional[int]
    polisher_args: tuple[str, ...]
    polisher_cwd: Optional[Path]
    emit_structure_snapshot: bool


@dataclass(slots=True)
class GenerateCommandResult:
    context: PipelineContext
    audit_path: Path
    review_engine_path: Path | None


class GenerateCommandError(Exception):
    """gen コマンドの実行失敗を表す例外。"""

    def __init__(self, message: str, *, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def build_analyzer_options(
    rules_config,
    template_style,
    *,
    emit_structure_snapshot: bool,
) -> AnalyzerOptions:
    analyzer_rules = rules_config.analyzer
    analyzer_defaults = AnalyzerOptions()
    body_font_size = template_style.body_font.size_pt
    body_font_color = template_style.body_font.color_hex
    primary_color = template_style.colors.primary
    background_color = template_style.colors.background

    max_bullet_level = (
        rules_config.max_bullet_level
        if rules_config.max_bullet_level is not None
        else analyzer_defaults.max_bullet_level
    )

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
        max_bullet_level=max_bullet_level,
        snapshot_output_filename="analysis_snapshot.json"
        if emit_structure_snapshot
        else None,
    )


def build_polisher_options(
    rules_config,
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
        executable = resolve_config_path(config.executable, base_dir=rules_path.parent)

    rules_file: Path | None = polisher_rules
    if rules_file is None and config.rules_path:
        rules_file = resolve_config_path(
            config.rules_path, base_dir=rules_path.parent
        )

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


def prepare_template_style(template: Path) -> tuple[TemplateStyle, dict[str, object]]:
    style, artifact = extract_template_style(template)
    if artifact.get("source", {}).get("type") == "default":
        error = artifact["source"].get("error")
        if error:
            click.echo(f"テンプレートスタイルの抽出に失敗しました: {error}", err=True)
    return style, artifact


def run_generate_command(config: GenerateCommandConfig) -> GenerateCommandResult:
    if not config.export_pdf and config.pdf_mode != "both":
        raise GenerateCommandError("--pdf-mode は --export-pdf と併用してください", exit_code=2)

    try:
        generate_ready = GenerateReadyDocument.parse_file(config.generate_ready_path)
    except Exception as exc:  # noqa: BLE001
        raise GenerateCommandError(
            f"generate_ready.json の読み込みに失敗しました: {exc}",
            exit_code=4,
        ) from exc

    template_path_value = generate_ready.meta.template_path
    if not template_path_value:
        raise GenerateCommandError(
            "generate_ready.json に template_path が含まれていません。stage 4 を最新仕様で再実行するか、テンプレート情報を埋め込んでください。",
            exit_code=2,
        )

    template_path = Path(template_path_value)
    if not template_path.is_absolute():
        candidate = (config.generate_ready_path.parent / template_path).resolve()
        template_path = candidate if candidate.exists() else template_path
    if not template_path.exists():
        raise GenerateCommandError(
            f"テンプレートファイルが見つかりません: {template_path}",
            exit_code=4,
        )

    rules_config = load_rules_config(config.rules_path)
    template_style, template_style_artifact = prepare_template_style(template_path)
    analyzer_options = build_analyzer_options(
        rules_config,
        template_style,
        emit_structure_snapshot=config.emit_structure_snapshot,
    )
    pdf_options = PdfExportOptions(
        enabled=config.export_pdf,
        mode=config.pdf_mode,
        output_filename=config.pdf_output,
        soffice_path=config.libreoffice_path,
        timeout_sec=config.pdf_timeout,
        max_retries=config.pdf_retries,
    )
    polisher_options = build_polisher_options(
        rules_config,
        polisher_toggle=config.polisher_toggle,
        polisher_path=config.polisher_path,
        polisher_rules=config.polisher_rules,
        polisher_timeout=config.polisher_timeout,
        polisher_args=config.polisher_args,
        polisher_cwd=config.polisher_cwd,
        rules_path=config.rules_path,
    )

    mapping_meta: dict[str, object] = {
        "generate_ready_path": str(config.generate_ready_path),
        "generate_ready_generated_at": generate_ready.meta.generated_at,
        "template_version": generate_ready.meta.template_version,
        "template_path": str(template_path),
    }

    base_artifacts: dict[str, object] = {
        "generate_ready": generate_ready,
        "generate_ready_path": str(config.generate_ready_path),
        "mapping_meta": mapping_meta,
    }

    mapping_log_path = config.generate_ready_path.with_name("mapping_log.json")
    if mapping_log_path.exists():
        base_artifacts["mapping_log_path"] = str(mapping_log_path)
        try:
            mapping_log = json.loads(mapping_log_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("mapping_log.json の読み込みに失敗しました: %s", exc)
        else:
            meta_payload = mapping_log.get("meta")
            if isinstance(meta_payload, dict):
                mapping_meta.update(meta_payload)
    fallback_path = config.generate_ready_path.with_name("fallback_report.json")
    if fallback_path.exists():
        base_artifacts["mapping_fallback_report_path"] = str(fallback_path)

    try:
        render_context = run_render_pipeline(
            generate_ready=generate_ready,
            generate_ready_path=config.generate_ready_path,
            output_dir=config.output_dir,
            template=template_path,
            pptx_name=config.pptx_name,
            template_style=template_style,
            template_style_artifact=template_style_artifact,
            analyzer_options=analyzer_options,
            pdf_options=pdf_options,
            polisher_options=polisher_options,
            base_artifacts=base_artifacts,
        )
    except PdfExportError as exc:
        raise GenerateCommandError(f"PDF 出力に失敗しました: {exc}", exit_code=5) from exc
    except PolisherError as exc:
        raise GenerateCommandError(f"Polisher の実行に失敗しました: {exc}", exit_code=6) from exc
    except FileNotFoundError as exc:
        raise GenerateCommandError(f"ファイルが見つかりません: {exc}", exit_code=4) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("パイプライン実行中にエラーが発生しました")
        raise GenerateCommandError("パイプライン実行中にエラーが発生しました", exit_code=1) from exc

    analysis_path = render_context.artifacts.get("analysis_path")
    review_engine_path = emit_review_engine_analysis(render_context, analysis_path)
    audit_path = write_audit_log(render_context)

    return GenerateCommandResult(
        context=render_context,
        audit_path=audit_path,
        review_engine_path=review_engine_path,
    )


def resolve_config_path(value: str, *, base_dir: Path | None = None) -> Path:
    resolved = find_config_path(value, base_dir=base_dir)
    if resolved is None and Path(value).name == "rules.json":
        # 後方互換: legacy 名称が指定された場合は pipeline_rules.json へのフォールバックも試す
        fallback = find_config_path(Path(value).with_name("pipeline_rules.json"), base_dir=base_dir)
        if fallback is not None:
            resolved = fallback
    if resolved is None:
        candidate = Path(value)
        msg = f"設定ファイルで指定されたパスが見つかりません: {candidate}"
        raise FileNotFoundError(msg)
    return resolved


def run_render_pipeline(
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
    base_artifacts: Optional[dict[str, object]] = None,
) -> PipelineContext:
    output_dir.mkdir(parents=True, exist_ok=True)

    render_spec = generate_ready_to_jobspec(generate_ready)
    artifacts = dict(base_artifacts or {})

    context = PipelineContext(
        spec=render_spec,
        workdir=output_dir,
        artifacts=artifacts,
    )
    context.add_artifact("template_style", template_style_artifact)
    context.add_artifact("template_style_data", template_style)
    context.add_artifact("generate_ready", generate_ready)
    if generate_ready_path is not None:
        context.add_artifact("generate_ready_path", str(generate_ready_path))

    template_source = getattr(generate_ready.meta, "template_source", "template")
    prototype_indices = [
        slide.meta.prototype_index
        for slide in generate_ready.slides
        if slide.meta.prototype_index is not None
    ]
    prototype_mapping = prototype_indices if prototype_indices else None
    if template_source == "slide" and template is None:
        raise RuntimeError(
            "template_source=slide の場合はテンプレート PPTX のパスが必要です。"
        )

    renderer = SimpleRendererStep(
        RenderingOptions(
            template_path=template,
            output_filename=pptx_name,
            template_style=template_style,
            template_source=template_source,
            prototype_mapping=prototype_mapping,
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

    steps = [
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


def emit_review_engine_analysis(
    context: PipelineContext,
    analysis_path: object | None,
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


def write_audit_log(context: PipelineContext) -> Path:
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
        "template_style": context.artifacts.get("template_style"),
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


def echo_render_outputs(context: PipelineContext, audit_path: Path | None) -> None:
    pptx_path = context.artifacts.get("pptx_path")
    if pptx_path is not None:
        click.echo(f"PPTX: {pptx_path}")
    else:
        click.echo("PPTX: --pdf-mode=only のため保存しませんでした")
    analysis_path = context.artifacts.get("analysis_path")
    click.echo(f"Analysis: {analysis_path}")
    baseline_analysis_path = context.artifacts.get(
        "analysis_pre_polisher_path")
    if baseline_analysis_path is not None:
        click.echo(f"Analysis (Pre-Polisher): {baseline_analysis_path}")
    rendering_log_path = context.artifacts.get("rendering_log_path")
    if rendering_log_path is not None:
        click.echo(f"Rendering Log: {rendering_log_path}")
    rendering_summary = context.artifacts.get("rendering_summary")
    if isinstance(rendering_summary, dict):
        click.echo(
            "Rendering Warnings: %s" % rendering_summary.get(
                "warnings_total", 0)
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
    fallback_report_path = context.artifacts.get(
        "mapping_fallback_report_path")
    if fallback_report_path is not None:
        click.echo(f"Fallback Report: {fallback_report_path}")
    monitoring_report_path = context.artifacts.get("monitoring_report_path")
    if monitoring_report_path is not None:
        click.echo(f"Monitoring Report: {monitoring_report_path}")
    if audit_path is not None:
        click.echo(f"Audit: {audit_path}")


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
