from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import click

from pptx_generator.models import DraftDocument, JobSpec
from pptx_generator.pipeline import (
    DraftStructuringOptions,
    DraftStructuringStep,
    PipelineContext,
    PipelineRunner,
    PipelineStep,
    PrepareNormalizationOptions,
    PrepareNormalizationStep,
)

from pptx_generator.stages.shared.common import dump_json, load_jobspec, resolve_layouts_path

logger = logging.getLogger(__name__)
@dataclass(slots=True)
class OutlineCommandConfig:
    spec_path: Path
    output_dir: Path
    target_length: int | None
    structure_pattern: str | None
    appendix_limit: int
    analysis_summary_path: Path | None
    prepare_cards: Path
    require_prepare: bool
    show_layout_reasons: bool
    draft_filename: str
    approved_filename: str
    log_filename: str
    generate_ready_filename: str
    generate_ready_meta_filename: str
    meta_filename: str


@dataclass(slots=True)
class OutlineResult:
    context: PipelineContext
    draft_path: Path
    approved_path: Path
    log_path: Path
    meta_path: Path
    generate_ready_path: Path
    generate_ready_meta_path: Path


def run_outline_command(config: OutlineCommandConfig) -> None:
    spec = load_jobspec(config.spec_path)

    try:
        layouts_path = resolve_layouts_path(spec=spec, spec_source=config.spec_path)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        raise click.exceptions.Exit(code=2) from exc

    try:
        result = execute_outline(
            spec=spec,
            layouts=layouts_path,
            output_dir=config.output_dir,
            spec_source_path=config.spec_path,
            target_length=config.target_length,
            structure_pattern=config.structure_pattern,
            appendix_limit=config.appendix_limit,
            analysis_summary_path=config.analysis_summary_path,
            prepare_cards=config.prepare_cards,
            require_prepare=config.require_prepare,
            draft_filename=config.draft_filename,
            approved_filename=config.approved_filename,
            log_filename=config.log_filename,
            generate_ready_filename=config.generate_ready_filename,
            generate_ready_meta_filename=config.generate_ready_meta_filename,
            meta_filename=config.meta_filename,
        )
    except FileNotFoundError as exc:
        click.echo(f"ファイルが見つかりません: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("outline 実行中にエラーが発生しました")
        raise click.exceptions.Exit(code=1) from exc

    print_outline_result(result, show_layout_reasons=config.show_layout_reasons)


def execute_outline(
    *,
    spec: JobSpec,
    layouts: Path | None,
    output_dir: Path,
    spec_source_path: Path,
    target_length: int | None,
    structure_pattern: str | None,
    appendix_limit: int,
    analysis_summary_path: Path | None,
    prepare_cards: Path | None,
    require_prepare: bool,
    draft_filename: str,
    approved_filename: str,
    log_filename: str,
    generate_ready_filename: str,
    generate_ready_meta_filename: str,
    meta_filename: str,
) -> OutlineResult:
    draft_options = DraftStructuringOptions(
        layouts_path=layouts,
        output_dir=output_dir,
        spec_source_path=spec_source_path,
        target_length=target_length,
        structure_pattern=structure_pattern,
        appendix_limit=appendix_limit,
        analysis_summary_path=analysis_summary_path,
        draft_store_dir=output_dir / "store",
    )

    context = run_draft_pipeline(
        spec=spec,
        output_dir=output_dir,
        prepare_cards=prepare_cards,
        require_prepare=require_prepare,
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

    ready_artifact = context.artifacts.get("generate_ready_path")
    ready_meta_artifact = context.artifacts.get("generate_ready_meta_path")
    ready_path = (
        Path(ready_artifact)
        if isinstance(ready_artifact, str)
        else (output_dir / generate_ready_filename)
    )
    ready_meta_path = (
        Path(ready_meta_artifact)
        if isinstance(ready_meta_artifact, str)
        else (output_dir / generate_ready_meta_filename)
    )

    return OutlineResult(
        context=context,
        draft_path=output_dir / draft_filename,
        approved_path=output_dir / approved_filename,
        log_path=output_dir / log_filename,
        meta_path=meta_path,
        generate_ready_path=ready_path,
        generate_ready_meta_path=ready_meta_path,
    )


def print_outline_result(result: OutlineResult, *, show_layout_reasons: bool) -> None:
    click.echo(f"Outline Draft: {result.draft_path}")
    click.echo(f"Outline Approved: {result.approved_path}")
    click.echo(f"Outline Review Log: {result.log_path}")
    click.echo(f"Outline Meta: {result.meta_path}")
    click.echo(f"Outline Generate Ready: {result.generate_ready_path}")
    click.echo(f"Outline Ready Meta: {result.generate_ready_meta_path}")

    if show_layout_reasons:
        context = result.context
        recommendations = context.artifacts.get("draft_layout_reasons")
        if isinstance(recommendations, list):
            click.echo("レイアウト推奨理由:")
            for entry in recommendations:
                click.echo(f"- {entry}")


def run_draft_pipeline(
    *,
    spec: JobSpec,
    output_dir: Path,
    prepare_cards: Path | None,
    require_prepare: bool,
    draft_options: DraftStructuringOptions,
) -> PipelineContext:
    output_dir.mkdir(parents=True, exist_ok=True)
    base_dir_for_store = draft_options.draft_store_dir
    if base_dir_for_store is None:
        candidate_base = draft_options.output_dir or output_dir
        base_dir_for_store = (candidate_base / "store") if candidate_base is not None else Path(".pptx/draft/store")
        draft_options.draft_store_dir = base_dir_for_store

    if prepare_cards is not None:
        resolved_cards = (
            prepare_cards if prepare_cards.is_absolute() else (Path.cwd() / prepare_cards)
        )
        resolved_cards = resolved_cards.resolve()
        try:
            display_path = resolved_cards.relative_to(Path.cwd())
        except ValueError:
            display_path = resolved_cards
        logger.info("prepare_card.json を読み込みます: %s", display_path)

    steps: list[PipelineStep] = [
        PrepareNormalizationStep(
            PrepareNormalizationOptions(
                cards_path=prepare_cards,
                require_document=require_prepare,
            )
        ),
        DraftStructuringStep(draft_options),
    ]

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
        template_mismatch = [
            item.model_dump(mode="json") for item in draft_document.meta.template_mismatch
        ]
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
    ready_path = context.artifacts.get("generate_ready_path")
    if isinstance(ready_path, str):
        paths["generate_ready"] = str(Path(ready_path).resolve())
    ready_meta_path = context.artifacts.get("generate_ready_meta_path")
    if isinstance(ready_meta_path, str):
        paths["generate_ready_meta"] = str(Path(ready_meta_path).resolve())

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
    dump_json(meta_path, meta_payload)
    return meta_path
