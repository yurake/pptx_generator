from __future__ import annotations

from pathlib import Path

from pptx_generator.cli_hooks.template_id import derive_template_id_from_template_path
from pptx_generator.cli_handlers.compose import ComposeCommandConfig, ComposeCommandError, run_compose_command
from pptx_generator.cli_handlers.prepare import PrepareCommandError
from pptx_generator.cli_handlers.rendering import GenerateCommandError
from pptx_generator.cli_handlers.template_commands import TemplateCommandConfig, TemplateCommandError, run_template_command
from pptx_generator.executive_board.common.script_runner import (
    run_prepare_scripts,
    run_compose_scripts,
    run_gen_scripts,
)

DRAFT_DIRNAME = "draft.json"

__all__ = [
    "build_template_job",
    "build_prepare_job",
    "build_compose_job",
    "build_gen_job",
    "TemplateCommandError",
    "PrepareCommandError",
    "ComposeCommandError",
    "GenerateCommandError",
]


def build_template_job(payload: dict, workdir: Path):
    layout_mode = payload.get("mode", "static")
    static_source = payload.get("static_source", "slide")
    effective_template_id = payload.get("template_id") or derive_template_id_from_template_path(
        Path(payload["template_path"])
    )
    config = TemplateCommandConfig(
        template_path=Path(payload["template_path"]),
        output_dir=workdir,
        format="json",
        layout=payload.get("layout"),
        anchor=payload.get("anchor"),
        layout_mode=layout_mode,
        static_source=static_source,
        template_ai_policy=None,
        template_ai_policy_id=None,
        disable_template_ai=False,
        with_release=bool(payload.get("with_release")),
        brand=payload.get("brand"),
        version=payload.get("version"),
        template_id=effective_template_id,
        release_output=workdir,
        generated_by=None,
        reviewed_by=None,
        baseline_release=None,
        golden_specs=(),
        slide_snapshot=bool(payload.get("slide_snapshot")),
        force=bool(payload.get("force")),
    )

    def run():
        result = run_template_command(config)
        artifacts = {
            "jobspec_url": str(workdir / "jobspec.json"),
            "template_spec_url": str(workdir / "template_spec.json"),
            "diagnostics_url": str(workdir / "diagnostics.json"),
        }
        return {"artifacts": artifacts, "result": result}

    return run


def build_prepare_job(payload: dict, workdir: Path, jobspec_path: Path, tx_root: Path):
    context_path = tx_root / "hook_context.json"
    prepare_inputs = list(payload.get("prepare_inputs", ()))

    def run():
        run_prepare_scripts(
            output_dir=workdir,
            jobspec_path=jobspec_path,
            prepare_inputs=prepare_inputs,
            context_path=context_path,
        )
        artifacts = {
            "prepare_card_url": str(workdir / "prepare_card.json"),
        }
        return {"artifacts": artifacts, "result": None}

    return run


def build_compose_job(payload: dict, workdir: Path, template_artifacts: dict, prepare_artifacts: dict):
    draft_log = workdir / DRAFT_DIRNAME / "draft_mapping_log.json"
    draft_log.parent.mkdir(parents=True, exist_ok=True)
    review_log = workdir / DRAFT_DIRNAME / "draft_review_log.json"
    generate_ready_path = workdir / "generate_ready.json"
    generate_ready_meta_path = workdir / "generate_ready_meta.json"
    context_path = workdir.parent / "hook_context.json"

    config = ComposeCommandConfig(
        spec_path=Path(template_artifacts["jobspec_url"]),
        draft_output=Path(workdir) / DRAFT_DIRNAME,
        target_length=None,
        structure_pattern=None,
        appendix_limit=10,
        analysis_summary_path=None,
        show_layout_reasons=bool(payload.get("show_layout_reasons", False)),
        output_dir=Path(workdir),
        rules_path=Path(payload.get("rules_path") or template_artifacts["diagnostics_url"]),
        prepare_cards=Path(prepare_artifacts["prepare_card_url"]),
        draft_filename=str(draft_log.name),
        approved_filename=str(review_log.name),
        log_filename=str(draft_log.name),
        meta_filename=str(review_log.name),
        generate_ready_filename=str(generate_ready_path.name),
        generate_ready_meta_filename=str(generate_ready_meta_path.name),
    )

    def run():
        run_compose_command(config)
        run_compose_scripts(
            generate_ready_path=generate_ready_path,
            output_dir=workdir,
            context_path=context_path,
        )
        artifacts = {
            "generate_ready_url": str(generate_ready_path),
            "generate_ready_meta_url": str(generate_ready_meta_path),
            "draft_mapping_log_url": str(draft_log),
            "draft_review_log_url": str(review_log),
        }
        return {"artifacts": artifacts, "result": None}

    return run


def build_gen_job(payload: dict, workdir: Path, compose_artifacts: dict, template_artifacts: dict):
    pptx_path = Path(workdir) / "proposal.pptx"
    pdf_path = Path(workdir) / "proposal.pdf"
    export_pdf = bool(payload.get("export_pdf", False))
    context_path = workdir.parent.parent / "hook_context.json"
    generate_ready_path = Path(compose_artifacts["generate_ready_url"])

    def run():
        if export_pdf:
            raise ValueError("export_pdf is not supported")
        run_gen_scripts(
            generate_ready_path=generate_ready_path,
            output_dir=workdir,
            pptx_name=pptx_path.name,
            context_path=context_path,
        )
        artifacts = {
            "pptx_url": str(pptx_path),
        }
        if payload.get("export_pdf"):
            artifacts["pdf_url"] = str(pdf_path)
        return {"artifacts": artifacts, "result": None}

    return run
