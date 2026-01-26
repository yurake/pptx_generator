from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pptx_generator.cli_handlers.common import dump_json
from pptx_generator.cli_handlers.compose import ComposeCommandConfig, ComposeCommandError, run_compose_command
from pptx_generator.cli_handlers.prepare import PrepareCommandConfig, PrepareCommandError, SLIDE_INPUTS_FILENAME, run_prepare_command
from pptx_generator.cli_handlers.rendering import GenerateCommandConfig, GenerateCommandError, run_generate_command
from pptx_generator.pipeline.text_edit import snapshot_shapes_for_edit
from pptx_generator.edit_ai import EditAIRequest, create_edit_ai_client
from pptx_generator.cli_handlers.template_commands import TemplateCommandConfig, TemplateCommandError, run_template_command
from pptx_generator.edit_ai.client import EditAIResponseFormatError
from pptx_generator.pipeline.edit_runner import EditRunError, run_edit_job

DRAFT_DIRNAME = "draft.json"

__all__ = [
    "build_template_job",
    "build_prepare_job",
    "build_compose_job",
    "build_gen_job",
    "build_edit_job",
    "TemplateCommandError",
    "PrepareCommandError",
    "ComposeCommandError",
    "GenerateCommandError",
    "EditCommandError",
]


class EditCommandError(RuntimeError):
    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


def build_template_job(payload: dict, workdir: Path):
    config = TemplateCommandConfig(
        template_path=Path(payload["template_path"]),
        output_dir=workdir,
        format="json",
        layout=payload.get("layout"),
        anchor=payload.get("anchor"),
        layout_mode=payload.get("mode", "static"),
        static_source="template",
        template_ai_policy=None,
        template_ai_policy_id=None,
        disable_template_ai=False,
        with_release=bool(payload.get("with_release")),
        brand=payload.get("brand"),
        version=payload.get("version"),
        template_id=payload.get("template_id"),
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
    default_jobspec = tx_root / "template" / "jobspec.json"
    prompts_dir = tx_root / "template" / "prompts"
    prepare_inputs = payload.get("prepare_inputs", ())
    prepare_path = payload.get("prepare_path")
    mode_value = payload.get("mode", "dynamic").lower()

    config = PrepareCommandConfig(
        prepare_path=prepare_path,
        prepare_inputs=prepare_inputs,
        output_dir=workdir,
        jobspec_path=jobspec_path,
        mode=mode_value,
        page_limit=payload.get("page_limit"),
        default_jobspec_path=default_jobspec,
        prompts_dirname=prompts_dir,
        slide_inputs_filename=SLIDE_INPUTS_FILENAME,
    )

    def run():
        result = run_prepare_command(config, dump_json=dump_json)
        artifacts = {
            "prepare_card_url": str(workdir / "prepare_card.json"),
            "prepare_log_url": str(workdir / "prepare_log.json"),
            "prepare_ai_log_url": str(workdir / "prepare_ai_log.json"),
            "ai_generation_meta_url": str(workdir / "ai_generation_meta.json"),
            "audit_log_url": str(workdir / "audit_log.json"),
        }
        return {"artifacts": artifacts, "result": result}

    return run


def build_compose_job(payload: dict, workdir: Path, template_artifacts: dict, prepare_artifacts: dict):
    draft_log = workdir / DRAFT_DIRNAME / "draft_mapping_log.json"
    draft_log.parent.mkdir(parents=True, exist_ok=True)
    review_log = workdir / DRAFT_DIRNAME / "draft_review_log.json"
    generate_ready_path = workdir / "generate_ready.json"
    generate_ready_meta_path = workdir / "generate_ready_meta.json"

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
        slide_alignment=bool(payload.get("slide_alignment", True)),
        slide_alignment_threshold=payload.get("slide_alignment_threshold"),
        slide_alignment_max_candidates=payload.get("slide_alignment_max_candidates"),
        draft_filename=str(draft_log.name),
        approved_filename=str(review_log.name),
        log_filename=str(draft_log.name),
        meta_filename=str(review_log.name),
        generate_ready_filename=str(generate_ready_path.name),
        generate_ready_meta_filename=str(generate_ready_meta_path.name),
    )

    def run():
        result = run_compose_command(config)
        artifacts = {
            "generate_ready_url": str(generate_ready_path),
            "generate_ready_meta_url": str(generate_ready_meta_path),
            "draft_mapping_log_url": str(draft_log),
            "draft_review_log_url": str(review_log),
        }
        return {"artifacts": artifacts, "result": result}

    return run


def build_gen_job(payload: dict, workdir: Path, compose_artifacts: dict, template_artifacts: dict):
    pptx_path = Path(workdir) / "proposal.pptx"
    pdf_path = Path(workdir) / "proposal.pdf"
    export_pdf = bool(payload.get("export_pdf", False))
    pdf_mode = payload.get("pdf_mode", "both") if export_pdf else "both"
    config = GenerateCommandConfig(
        generate_ready_path=Path(compose_artifacts["generate_ready_url"]),
        output_dir=Path(workdir),
        pptx_name=pptx_path.name,
        rules_path=Path(payload.get("rules_path") or template_artifacts.get("diagnostics_url") or ".pptx/template/diagnostics.json"),
        export_pdf=export_pdf,
        pdf_mode=pdf_mode,
        pdf_output=str(pdf_path) if export_pdf else None,
        libreoffice_path=None,
        pdf_timeout=payload.get("pdf_timeout", 120),
        pdf_retries=payload.get("pdf_retries", 1),
        polisher_toggle=None,
        polisher_path=None,
        polisher_rules=None,
        polisher_timeout=None,
        polisher_args=(),
        polisher_cwd=None,
        emit_structure_snapshot=bool(payload.get("emit_structure_snapshot", False)),
    )

    def run():
        result = run_generate_command(config)
        artifacts = {
            "pptx_url": str(pptx_path),
        }
        if payload.get("export_pdf"):
            artifacts["pdf_url"] = str(pdf_path)
        return {"artifacts": artifacts, "result": result}

    return run


def build_edit_job(payload: dict, workdir: Path):
    pptx_path = Path(payload["pptx_path"]).expanduser()
    if not pptx_path.exists():
        raise EditCommandError(f"pptx_path not found: {pptx_path}")

    config = {
        "edits_json": payload.get("edits_json"),
        "edits_inline": payload.get("edits"),
        "output_path": Path(payload.get("output") or (workdir / pptx_path.name)).expanduser(),
    }

    def run():
        try:
            return run_edit_job(
                pptx_path=pptx_path,
                edits_json=config["edits_json"],
                edits_inline=config["edits_inline"],
                output_path=config["output_path"],
                snapshot_fn=snapshot_shapes_for_edit,
                client_factory=create_edit_ai_client,
                error_cls=EditCommandError,
            )
        except EditRunError as exc:
            raise EditCommandError(str(exc)) from exc
        except EditAIResponseFormatError as exc:
            # LLM 応答不正もユーザー向けエラーとして扱う
            raise EditCommandError(str(exc)) from exc

    return run
