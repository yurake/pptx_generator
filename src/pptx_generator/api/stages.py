from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pptx_generator.cli_handlers.common import dump_json
from pptx_generator.cli_commands.prepare import (
    build_prepare_config,
    build_stage_env,
    determine_primary_prepare_path,
    load_hook_manager_if_static,
    normalize_prepare_inputs,
    run_post_slide_hooks,
    run_pre_slide_hooks,
    run_stage_hook_if_needed,
)
from pptx_generator.cli_hooks import extract_template_id_from_json_file, load_hooks_for_template_id
from pptx_generator.cli_hooks.slides import slide_contexts_from_generate_ready
from pptx_generator.cli_hooks.template_id import derive_template_id_from_template_path
from pptx_generator.cli_commands.hook_runner import (
    load_stage_hooks,
    run_post_stage_slide_hooks,
    run_slide_hooks,
    run_stage_hook,
)
from pptx_generator.cli_handlers.compose import ComposeCommandConfig, ComposeCommandError, run_compose_command
from pptx_generator.cli_handlers.prepare import PrepareCommandError, SLIDE_INPUTS_FILENAME, run_prepare_command
from pptx_generator.cli_handlers.rendering import GenerateCommandConfig, GenerateCommandError, run_generate_command
from pptx_generator.cli_handlers.template_commands import TemplateCommandConfig, TemplateCommandError, run_template_command

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
    stage_env = {
        "PPTX_STAGE": "template",
        "PPTX_TEMPLATE_ID": effective_template_id,
        "PPTX_TEMPLATE_PATH": str(Path(payload["template_path"]).resolve()),
        "PPTX_STAGE_OUTPUT_DIR": str(workdir.resolve()),
        "PPTX_LAYOUT_MODE": str(layout_mode).lower(),
        "PPTX_TEMPLATE_FORMAT": "json",
        "PPTX_TEMPLATE_LAYOUT_FILTER": payload.get("layout") or "",
        "PPTX_TEMPLATE_ANCHOR_FILTER": payload.get("anchor") or "",
        "PPTX_TEMPLATE_WITH_RELEASE": "1" if payload.get("with_release") else "0",
        "PPTX_TEMPLATE_BRAND": payload.get("brand") or "",
        "PPTX_TEMPLATE_VERSION": payload.get("version") or "",
        "PPTX_TEMPLATE_RELEASE_OUTPUT": str(workdir.resolve()),
        "PPTX_TEMPLATE_BASELINE_RELEASE": "",
        "PPTX_TEMPLATE_GOLDEN_SPEC_COUNT": "0",
        "PPTX_TEMPLATE_AI_POLICY": "",
        "PPTX_TEMPLATE_AI_POLICY_ID": "",
        "PPTX_TEMPLATE_DISABLE_AI": "",
        "PPTX_TEMPLATE_STATIC_SOURCE": static_source,
        "PPTX_TEMPLATE_SLIDE_SNAPSHOT": "1" if payload.get("slide_snapshot") else "0",
        "PPTX_TEMPLATE_FORCE": "1" if payload.get("force") else "0",
    }
    hook_manager = None
    if str(layout_mode).lower() == "static":
        hook_manager = load_hooks_for_template_id(effective_template_id)

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
        if hook_manager:
            executed, continue_default = hook_manager.run_stage_hook(
                "template",
                env=stage_env,
            )
            if executed and not continue_default:
                artifacts = {
                    "jobspec_url": str(workdir / "jobspec.json"),
                    "template_spec_url": str(workdir / "template_spec.json"),
                    "diagnostics_url": str(workdir / "diagnostics.json"),
                }
                return {"artifacts": artifacts, "result": None}

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
    context_path = tx_root / "hook_context.json"
    prepare_inputs = tuple(payload.get("prepare_inputs", ()))
    prepare_path = payload.get("prepare_path")
    mode_value = payload.get("mode", "dynamic").lower()

    def run():
        normalized_inputs = normalize_prepare_inputs(prepare_inputs)
        primary_prepare_path = determine_primary_prepare_path(normalized_inputs)
        stage_env = build_stage_env(
            mode=mode_value,
            primary_prepare_path=primary_prepare_path,
            normalized_inputs=normalized_inputs,
            output_dir=workdir,
            jobspec_path=jobspec_path,
            page_limit=payload.get("page_limit"),
        )
        stage_env["PPTX_CONTEXT_PATH"] = str(context_path.resolve())
        hook_manager, template_id = load_hook_manager_if_static(
            mode=mode_value,
            jobspec_path=jobspec_path,
            stage_env=stage_env,
        )
        if hook_manager is None and mode_value == "static":
            template_id = extract_template_id_from_json_file(jobspec_path)
            if template_id:
                hook_manager = load_hooks_for_template_id(template_id)
                if hook_manager:
                    stage_env["PPTX_TEMPLATE_ID"] = template_id
        if not run_stage_hook_if_needed(
            hook_manager=hook_manager,
            template_id=template_id,
            stage_env=stage_env,
        ):
            artifacts = {
                "prepare_card_url": str(workdir / "prepare_card.json"),
                "prepare_log_url": str(workdir / "prepare_log.json"),
                "prepare_ai_log_url": str(workdir / "prepare_ai_log.json"),
                "ai_generation_meta_url": str(workdir / "ai_generation_meta.json"),
                "audit_log_url": str(workdir / "audit_log.json"),
            }
            return {"artifacts": artifacts, "result": None}

        config = build_prepare_config(
            prepare_path=primary_prepare_path,
            prepare_inputs=tuple(normalized_inputs),
            output_dir=workdir,
            jobspec=jobspec_path,
            mode=mode_value,
            page_limit=payload.get("page_limit"),
            default_jobspec_path=default_jobspec,
            prompts_dirname=prompts_dir,
            slide_inputs_filename=SLIDE_INPUTS_FILENAME,
        )

        contexts, executed = run_pre_slide_hooks(
            hook_manager=hook_manager,
            template_id=template_id,
            jobspec_path=jobspec_path,
            stage_env=stage_env,
        )
        if not executed and hook_manager:
            executed = hook_manager.run_slide_hooks(
                "prepare",
                slides=[],
                env=stage_env,
                continue_default_filter=False,
                allow_fallback_context=True,
            )

        if executed:
            artifacts = {
                "prepare_card_url": str(workdir / "prepare_card.json"),
                "prepare_log_url": str(workdir / "prepare_log.json"),
                "prepare_ai_log_url": str(workdir / "prepare_ai_log.json"),
                "ai_generation_meta_url": str(workdir / "ai_generation_meta.json"),
                "audit_log_url": str(workdir / "audit_log.json"),
            }
            return {"artifacts": artifacts, "result": None}

        result = run_prepare_command(config, dump_json=dump_json)
        run_post_slide_hooks(
            hook_manager=hook_manager,
            template_id=template_id,
            stage_env=stage_env,
            contexts=contexts,
            result=result,
        )
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
    context_path = workdir.parent / "hook_context.json"
    hook_manager, template_id = load_stage_hooks(Path(template_artifacts["jobspec_url"]))
    stage_env = {
        "PPTX_STAGE": "compose",
        "PPTX_SPEC_PATH": str(Path(template_artifacts["jobspec_url"]).resolve()),
        "PPTX_OUTPUT_DIR": str(workdir.resolve()),
        "PPTX_DRAFT_OUTPUT": str((workdir / DRAFT_DIRNAME).resolve()),
        "PPTX_TARGET_LENGTH": "",
        "PPTX_STRUCTURE_PATTERN": "",
        "PPTX_APPENDIX_LIMIT": "10",
        "PPTX_ANALYSIS_SUMMARY_PATH": "",
        "PPTX_SHOW_LAYOUT_REASONS": "1" if payload.get("show_layout_reasons", False) else "0",
        "PPTX_RULES_PATH": str(Path(payload.get("rules_path") or template_artifacts["diagnostics_url"]).resolve()),
        "PPTX_PREPARE_CARDS_PATH": str(Path(prepare_artifacts["prepare_card_url"]).resolve()),
        "PPTX_CONTEXT_PATH": str(context_path.resolve()),
    }
    if template_id:
        stage_env["PPTX_TEMPLATE_ID"] = template_id

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
        if run_stage_hook(
            "compose",
            hook_manager=hook_manager,
            template_id=template_id,
            stage_env=stage_env,
        ):
            artifacts = {
                "generate_ready_url": str(generate_ready_path),
                "generate_ready_meta_url": str(generate_ready_meta_path),
                "draft_mapping_log_url": str(draft_log),
                "draft_review_log_url": str(review_log),
            }
            return {"artifacts": artifacts, "result": None}

        contexts = slide_contexts_from_generate_ready(Path(prepare_artifacts["prepare_card_url"]))
        if run_slide_hooks(
            "compose",
            hook_manager=hook_manager,
            stage_env=stage_env,
            slides=contexts,
            continue_default_filter=False,
        ):
            artifacts = {
                "generate_ready_url": str(generate_ready_path),
                "generate_ready_meta_url": str(generate_ready_meta_path),
                "draft_mapping_log_url": str(draft_log),
                "draft_review_log_url": str(review_log),
            }
            return {"artifacts": artifacts, "result": None}

        result = run_compose_command(config)
        run_post_stage_slide_hooks(
            "compose",
            hook_manager=hook_manager,
            template_id=template_id,
            base_stage_env=stage_env,
            generate_ready_path=generate_ready_path,
            slide_context_loader=slide_contexts_from_generate_ready,
        )
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
    context_path = workdir.parent.parent / "hook_context.json"
    generate_ready_path = Path(compose_artifacts["generate_ready_url"])
    template_id = extract_template_id_from_json_file(generate_ready_path)
    hook_manager = load_hooks_for_template_id(template_id) if template_id else None
    rules_path = Path(
        payload.get("rules_path")
        or template_artifacts.get("diagnostics_url")
        or ".pptx/template/diagnostics.json"
    )
    stage_env = {
        "PPTX_STAGE": "gen",
        "PPTX_GENERATE_READY_PATH": str(generate_ready_path.resolve()),
        "PPTX_OUTPUT_DIR": str(workdir.resolve()),
        "PPTX_PPTX_NAME": pptx_path.name,
        "PPTX_RULES_PATH": str(rules_path.resolve()),
        "PPTX_CONTEXT_PATH": str(context_path.resolve()),
        "PPTX_EXPORT_PDF": "1" if export_pdf else "0",
        "PPTX_PDF_MODE": pdf_mode,
        "PPTX_PDF_OUTPUT": str(pdf_path.name) if export_pdf else "",
        "PPTX_LIBREOFFICE_PATH": "",
        "PPTX_PDF_TIMEOUT": str(payload.get("pdf_timeout", 120)),
        "PPTX_PDF_RETRIES": str(payload.get("pdf_retries", 1)),
        "PPTX_POLISHER_TOGGLE": "",
        "PPTX_POLISHER_PATH": "",
        "PPTX_POLISHER_RULES": "",
        "PPTX_POLISHER_TIMEOUT": "",
        "PPTX_POLISHER_ARGS": "",
        "PPTX_POLISHER_CWD": "",
        "PPTX_EMIT_STRUCTURE_SNAPSHOT": "1" if payload.get("emit_structure_snapshot", False) else "0",
    }
    if template_id:
        stage_env["PPTX_TEMPLATE_ID"] = template_id
    if context_path.exists():
        try:
            context_payload = json.loads(context_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            context_payload = {}
        schedule_md = context_payload.get("schedule_md_path")
        if isinstance(schedule_md, str) and schedule_md.strip():
            stage_env["PPTX_SCHEDULE_MD"] = schedule_md.strip()
    config = GenerateCommandConfig(
        generate_ready_path=generate_ready_path,
        output_dir=Path(workdir),
        pptx_name=pptx_path.name,
        rules_path=rules_path,
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
        if hook_manager:
            executed, continue_default = hook_manager.run_stage_hook(
                "gen",
                env=stage_env,
            )
            if executed and not continue_default:
                artifacts = {"pptx_url": str(pptx_path)}
                if export_pdf:
                    artifacts["pdf_url"] = str(pdf_path)
                return {"artifacts": artifacts, "result": None}

            contexts = slide_contexts_from_generate_ready(generate_ready_path)
            executed = hook_manager.run_slide_hooks(
                "gen",
                slides=contexts,
                env=stage_env,
                continue_default_filter=False,
                allow_fallback_context=True,
            )
            if executed:
                artifacts = {"pptx_url": str(pptx_path)}
                if export_pdf:
                    artifacts["pdf_url"] = str(pdf_path)
                return {"artifacts": artifacts, "result": None}

        result = run_generate_command(config)
        if hook_manager and template_id:
            stage_env_with_outputs = dict(stage_env)
            stage_env_with_outputs["PPTX_OUTPUT_PPTX_PATH"] = str(pptx_path.resolve())
            if export_pdf:
                stage_env_with_outputs["PPTX_OUTPUT_PDF_PATH"] = str(pdf_path.resolve())
            contexts = slide_contexts_from_generate_ready(generate_ready_path)
            hook_manager.run_slide_hooks(
                "gen",
                slides=contexts,
                env=stage_env_with_outputs,
                continue_default_filter=True,
                allow_fallback_context=True,
            )
        artifacts = {
            "pptx_url": str(pptx_path),
        }
        if payload.get("export_pdf"):
            artifacts["pdf_url"] = str(pdf_path)
        return {"artifacts": artifacts, "result": result}

    return run
