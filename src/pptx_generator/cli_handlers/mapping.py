from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import click

from pptx_generator.generate_ready import generate_ready_to_jobspec
from pptx_generator.models import (
    GenerateReadyDocument,
    JobMeta,
    JobSpec,
    SpecValidationError,
    TemplateStyle,
)
from pptx_generator.pipeline import (
    DraftStructuringOptions,
    MappingOptions,
    MappingStep,
    PipelineContext,
    PipelineRunner,
    PipelineStep,
    PrepareNormalizationError,
    RefinerOptions,
    SimpleRefinerStep,
    SpecValidatorStep,
)
from pptx_generator.settings import RulesConfig
from pptx_generator.settings.loader import load_rules_config

from .common import (
    dump_json,
    load_jobspec,
    resolve_layouts_path,
    resolve_template_path,
)
from .outline import run_draft_pipeline

logger = logging.getLogger(__name__)

DEFAULT_GENERATE_READY_FILENAME = "generate_ready.json"
DEFAULT_GENERATE_READY_META_FILENAME = "generate_ready_meta.json"


@dataclass(slots=True)
class TemplateStylePayload:
    style: TemplateStyle
    artifact: dict[str, object]


@dataclass(slots=True)
class MappingPipelineConfig:
    spec: JobSpec
    output_dir: Path
    spec_source_path: Path
    rules_config: RulesConfig
    refiner_options: RefinerOptions
    template_style: TemplateStylePayload
    prepare_cards: Path | None
    require_prepare: bool
    layouts: Path | None
    draft_output: Path
    template: Path | None


@dataclass(slots=True)
class MappingCommandConfig:
    spec_path: Path
    output_dir: Path
    rules_path: Path
    draft_output: Path
    prepare_cards: Path
    generate_ready_filename: str = DEFAULT_GENERATE_READY_FILENAME
    generate_ready_meta_filename: str = DEFAULT_GENERATE_READY_META_FILENAME


@dataclass(slots=True)
class MappingCommandResult:
    context: PipelineContext


class MappingCommandError(Exception):
    """mapping コマンド実行時の失敗を表す例外。"""

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


def prepare_template_style(template: Path) -> TemplateStylePayload:
    from pptx_generator.template_style import extract_template_style

    style, artifact = extract_template_style(template)
    if artifact.get("source", {}).get("type") == "default":
        error = artifact["source"].get("error")
        if error:
            click.echo(f"テンプレートスタイルの抽出に失敗しました: {error}", err=True)
    return TemplateStylePayload(style=style, artifact=artifact)


def build_refiner_options(
    rules_config: RulesConfig,
    template_style: TemplateStyle,
) -> RefinerOptions:
    analyzer_rules = rules_config.analyzer
    refiner_rules = rules_config.refiner
    body_font_size = template_style.body_font.size_pt
    body_font_color = template_style.body_font.color_hex
    primary_color = template_style.colors.primary

    defaults = RefinerOptions()
    max_bullet_level = (
        rules_config.max_bullet_level
        if rules_config.max_bullet_level is not None
        else defaults.max_bullet_level
    )


def run_mapping_command(config: MappingCommandConfig) -> MappingCommandResult:
    try:
        spec = load_jobspec(config.spec_path)
    except SpecValidationError as exc:
        raise MappingCommandError(
            "スキーマ検証に失敗しました",
            exit_code=2,
            errors=exc.errors,
        ) from exc

    try:
        resolved_template = resolve_template_path(spec=spec, spec_source=config.spec_path)
    except ValueError as exc:
        raise MappingCommandError(str(exc), exit_code=2) from exc

    try:
        resolved_layouts = resolve_layouts_path(spec=spec, spec_source=config.spec_path)
    except ValueError as exc:
        raise MappingCommandError(str(exc), exit_code=2) from exc

    rules_config = load_rules_config(config.rules_path)
    template_style_payload = prepare_template_style(resolved_template)
    refiner_options = build_refiner_options(rules_config, template_style_payload.style)

    pipeline_config = MappingPipelineConfig(
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

    try:
        context = run_mapping_pipeline(
            params=pipeline_config,
            generate_ready_filename=config.generate_ready_filename,
            generate_ready_meta_filename=config.generate_ready_meta_filename,
        )
    except ValueError as exc:
        raise MappingCommandError(str(exc), exit_code=2) from exc
    except SpecValidationError as exc:
        raise MappingCommandError("業務ルール検証に失敗しました", exit_code=3) from exc
    except PrepareNormalizationError as exc:
        raise MappingCommandError(f"プレペア成果物の読み込みに失敗しました: {exc}", exit_code=4) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("マッピング実行中にエラーが発生しました")
        raise MappingCommandError("マッピング実行中にエラーが発生しました", exit_code=1) from exc

    return MappingCommandResult(context=context)

    return RefinerOptions(
        max_bullet_level=max_bullet_level,
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
        default_font_name=template_style.body_font.name,
    )


def run_mapping_pipeline(
    *,
    params: MappingPipelineConfig,
    draft_context: PipelineContext | None = None,
    draft_options: Optional[DraftStructuringOptions] = None,
    generate_ready_filename: str,
    generate_ready_meta_filename: str,
) -> PipelineContext:
    if params.template is None:
        msg = "jobspec.meta.template_path を設定し、テンプレートパスを埋め込んでください。"
        raise ValueError(msg)

    params.output_dir.mkdir(parents=True, exist_ok=True)
    params.draft_output.mkdir(parents=True, exist_ok=True)

    mapping_options = MappingOptions(
        layouts_path=params.layouts,
        output_dir=params.output_dir,
        template_path=params.template,
    )

    if draft_context is None:
        draft_context = run_draft_pipeline(
            spec=params.spec,
            output_dir=params.draft_output,
            prepare_cards=params.prepare_cards,
            require_prepare=params.require_prepare,
            draft_options=draft_options
            or DraftStructuringOptions(
                layouts_path=params.layouts,
                output_dir=params.draft_output,
                spec_source_path=params.spec_source_path,
            ),
        )
    elif draft_context.workdir != params.draft_output:
        logger.debug(
            "draft_context.workdir と draft_output が一致しません: %s != %s",
            draft_context.workdir,
            params.draft_output,
        )

    draft_generate_ready = draft_context.artifacts.get("generate_ready")
    if (
        isinstance(draft_generate_ready, GenerateReadyDocument)
        and draft_generate_ready.meta.layout_mode == "static"
    ):
        return _pass_through_static_generate_ready(
            spec=params.spec,
            draft_context=draft_context,
            output_dir=params.output_dir,
            mapping_options=mapping_options,
            generate_ready_filename=generate_ready_filename,
            generate_ready_meta_filename=generate_ready_meta_filename,
        )

    context = PipelineContext(
        spec=params.spec,
        workdir=params.output_dir,
        artifacts=dict(draft_context.artifacts),
    )
    context.add_artifact("template_style", params.template_style.artifact)
    context.add_artifact("template_style_data", params.template_style.style)
    steps: list[PipelineStep] = [
        SpecValidatorStep(
            max_title_length=params.rules_config.max_title_length,
            max_bullet_length=params.rules_config.max_bullet_length,
            max_bullet_level=params.rules_config.max_bullet_level,
            forbidden_words=params.rules_config.forbidden_words,
        ),
        SimpleRefinerStep(params.refiner_options),
        MappingStep(mapping_options),
    ]
    PipelineRunner(steps).execute(context)

    _ensure_generate_ready_meta(
        context=context,
        output_dir=params.output_dir,
        filename=generate_ready_meta_filename,
    )
    return context


def echo_mapping_outputs(context: PipelineContext) -> None:
    generate_ready_path = context.artifacts.get("generate_ready_path")
    if generate_ready_path is not None:
        click.echo(f"Generate Ready: {generate_ready_path}")
    mapping_log_path = context.artifacts.get("mapping_log_path")
    if mapping_log_path is not None:
        click.echo(f"Mapping Log: {mapping_log_path}")
    fallback_report_path = context.artifacts.get("mapping_fallback_report_path")
    if fallback_report_path is not None:
        click.echo(f"Fallback Report: {fallback_report_path}")


def _pass_through_static_generate_ready(
    *,
    spec: JobSpec,
    draft_context: PipelineContext,
    output_dir: Path,
    mapping_options: MappingOptions,
    generate_ready_filename: str,
    generate_ready_meta_filename: str,
) -> PipelineContext:
    ready_doc = draft_context.artifacts.get("generate_ready")
    if not isinstance(ready_doc, GenerateReadyDocument):
        raise RuntimeError("static モードの generate_ready が見つかりません")

    output_dir.mkdir(parents=True, exist_ok=True)

    template_path: str | None = None
    if mapping_options.template_path is not None:
        template_path = str(mapping_options.template_path)
    elif isinstance(spec.meta, JobMeta) and spec.meta.template_path:
        template_path = spec.meta.template_path
    else:
        raw_meta = getattr(spec, "meta", None)
        if isinstance(raw_meta, dict):
            raw_template = raw_meta.get("template_path")
            if isinstance(raw_template, str):
                template_path = raw_template

    if template_path:
        meta_updates = {"template_path": template_path}
        job_meta = ready_doc.meta.job_meta
        if job_meta is not None and not job_meta.template_path:
            meta_updates["job_meta"] = job_meta.model_copy(
                update={"template_path": template_path}
            )
        ready_doc = ready_doc.model_copy(
            update={"meta": ready_doc.meta.model_copy(update=meta_updates)}
        )
        logger.debug("static pass-through: template_path set to %s", template_path)

    ready_path = output_dir / generate_ready_filename
    dump_json(ready_path, ready_doc.model_dump(mode="json", exclude_none=True))

    meta_payload: dict[str, object] | None = None
    meta_source = draft_context.artifacts.get("generate_ready_meta_path")
    if isinstance(meta_source, str):
        meta_path = Path(meta_source)
        if meta_path.exists():
            try:
                meta_payload = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                meta_payload = None

    if meta_payload is None:
        meta_payload = generate_ready_to_jobspec(ready_doc)
    else:
        if template_path:
            meta_payload["template_path"] = template_path
        if "mode" not in meta_payload and ready_doc.meta.layout_mode:
            meta_payload["mode"] = ready_doc.meta.layout_mode
        if ready_doc.meta.slot_summary:
            meta_payload.setdefault("slot_summary", ready_doc.meta.slot_summary)
        meta_payload.setdefault(
            "generate_ready_generated_at", ready_doc.meta.generated_at
        )

    ready_meta_path = output_dir / generate_ready_meta_filename
    dump_json(ready_meta_path, meta_payload)

    mapping_log_dest = output_dir / mapping_options.mapping_log_filename
    draft_mapping_log_path = draft_context.artifacts.get("draft_mapping_log_path")
    if isinstance(draft_mapping_log_path, str):
        mapping_src = Path(draft_mapping_log_path)
        if mapping_src.exists():
            if mapping_src.resolve() != mapping_log_dest.resolve():
                mapping_log_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(mapping_src, mapping_log_dest)
            else:
                mapping_log_dest = mapping_src
    else:
        draft_mapping_log = draft_context.artifacts.get("draft_mapping_log")
        if draft_mapping_log is not None:
            dump_json(mapping_log_dest, draft_mapping_log)

    context = PipelineContext(spec=spec, workdir=output_dir)
    context.artifacts.update(
        {
            "generate_ready": ready_doc,
            "generate_ready_path": str(ready_path),
            "generate_ready_meta_path": str(ready_meta_path),
        }
    )
    if mapping_log_dest.exists():
        context.add_artifact("mapping_log_path", str(mapping_log_dest))
    mapping_meta = {
        "mode": "static",
        "slot_summary": ready_doc.meta.slot_summary or {},
        "generate_ready_generated_at": ready_doc.meta.generated_at,
        "template_path": ready_doc.meta.template_path,
        "blueprint_path": ready_doc.meta.blueprint_path,
        "blueprint_hash": ready_doc.meta.blueprint_hash,
    }
    context.add_artifact("mapping_meta", mapping_meta)
    return context


def _ensure_generate_ready_meta(
    *,
    context: PipelineContext,
    output_dir: Path,
    filename: str,
) -> None:
    meta_source = context.artifacts.get("generate_ready_meta_path")
    if not isinstance(meta_source, str):
        return

    source_path = Path(meta_source)
    destination = output_dir / filename
    try:
        if source_path.exists():
            if destination.resolve() != source_path.resolve():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination)
            context.add_artifact("generate_ready_meta_path", str(destination))
    except OSError as exc:  # noqa: PERF203
        raise RuntimeError(
            f"generate_ready_meta.json のコピーに失敗しました: {exc}"
        ) from exc
