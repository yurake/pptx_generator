"""pptx_generator CLI."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from .cli_handlers import (
    PROMPT_USER_SECTION_END,  # noqa: F401 - re-exported for downstream usage
    PROMPT_USER_SECTION_START,  # noqa: F401 - re-exported for downstream usage
    SLIDE_INPUTS_FILENAME,
    PrepareCommandConfig,
)
from .cli_handlers.common import (
    configure_llm_logger,
    determine_log_level,
)
from .cli_commands import (
    build_prepare_config as _build_prepare_config,
    create_compose_command,
    create_edit_command,
    create_gen_command,
    create_layout_validate_command,
    create_mapping_command,
    create_outline_command,
    create_prepare_command,
    create_template_command,
    create_tpl_extract_command,
    create_tpl_release_command,
)
from .pipeline import DraftStructuringOptions
from .logging import configure_root_logging
from .settings import RulesConfig  # noqa: F401 - re-exported for compatibility
from .cli_handlers.template_extraction import (
    PROMPT_TEMPLATE_DIRNAME,
)
from .settings.paths import get_default_config_path, get_output_root, build_output_dir

DEFAULT_RULES_PATH = get_default_config_path("pipeline_rules.json")
DEFAULT_GEN_PPTX_NAME = "proposal.pptx"
DEFAULT_GEN_PDF_OUTPUT = "proposal.pdf"
DEFAULT_GEN_PDF_TIMEOUT = 120
DEFAULT_GEN_PDF_RETRIES = 2
DEFAULT_TEMPLATE_LAYOUT_MODE = "dynamic"
DEFAULT_APPENDIX_LIMIT = 5
PREPARE_CARD_FILENAME = "prepare_card.json"

logger = logging.getLogger(__name__)

_determine_log_level = determine_log_level


_DEFAULT_DRAFT_OPTIONS = DraftStructuringOptions()
DEFAULT_DRAFT_FILENAME = _DEFAULT_DRAFT_OPTIONS.draft_filename
DEFAULT_APPROVED_FILENAME = _DEFAULT_DRAFT_OPTIONS.approved_filename
DEFAULT_DRAFT_LOG_FILENAME = _DEFAULT_DRAFT_OPTIONS.log_filename
DEFAULT_GENERATE_READY_FILENAME = _DEFAULT_DRAFT_OPTIONS.generate_ready_filename
DEFAULT_GENERATE_READY_META_FILENAME = _DEFAULT_DRAFT_OPTIONS.generate_ready_meta_filename
DEFAULT_DRAFT_META_FILENAME = "draft_meta.json"


def build_prepare_config(
    *,
    prepare_path: Path | None,
    prepare_inputs: tuple[str, ...],
    output_dir: Path,
    jobspec: Path | None,
    mode: str,
    page_limit: int | None,
) -> PrepareCommandConfig:
    return _build_prepare_config(
        prepare_path=prepare_path,
        prepare_inputs=prepare_inputs,
        output_dir=output_dir,
        jobspec=jobspec,
        mode=mode,
        page_limit=page_limit,
        default_jobspec_path=DEFAULT_JOBSPEC_PATH,
        prompts_dirname=PROMPT_TEMPLATE_DIRNAME,
        slide_inputs_filename=SLIDE_INPUTS_FILENAME,
    )


load_dotenv()

_OUTPUT_ROOT = get_output_root()
DEFAULT_TEMPLATE_OUTPUT_DIR = build_output_dir("template", root=_OUTPUT_ROOT)
DEFAULT_TEMPLATE_RELEASE_OUTPUT_DIR = build_output_dir("release", root=_OUTPUT_ROOT)
DEFAULT_PREPARE_OUTPUT_DIR = build_output_dir("prepare", root=_OUTPUT_ROOT)
DEFAULT_JOBSPEC_PATH = DEFAULT_TEMPLATE_OUTPUT_DIR / "jobspec.json"
DEFAULT_DRAFT_OUTPUT_DIR = build_output_dir("draft", root=_OUTPUT_ROOT)
DEFAULT_COMPOSE_OUTPUT_DIR = build_output_dir("compose", root=_OUTPUT_ROOT)
DEFAULT_GEN_OUTPUT_DIR = build_output_dir("gen", root=_OUTPUT_ROOT)
DEFAULT_VALIDATION_OUTPUT_DIR = build_output_dir("validation", root=_OUTPUT_ROOT)
@click.group(
    help="JSON 仕様から PPTX を生成する CLI",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("-v", "--verbose", is_flag=True, help="INFO レベルの冗長ログを出力する")
@click.option("--debug", is_flag=True, help="DEBUG レベルで詳細ログを出力する")
def app(verbose: bool, debug: bool) -> None:
    """CLI ルートエントリ。"""
    level, deferred_logs = determine_log_level(verbose, debug)
    configure_root_logging(level=level)
    logging.getLogger("openai").setLevel(level)
    cli_logger = logging.getLogger("pptx_generator.cli")
    for message_level, message in deferred_logs:
        cli_logger.log(message_level, message)
    configure_llm_logger()


gen = create_gen_command(
    default_output_dir=DEFAULT_GEN_OUTPUT_DIR,
    default_pptx_name=DEFAULT_GEN_PPTX_NAME,
    default_rules_path=DEFAULT_RULES_PATH,
    default_pdf_output=DEFAULT_GEN_PDF_OUTPUT,
    default_pdf_timeout=DEFAULT_GEN_PDF_TIMEOUT,
    default_pdf_retries=DEFAULT_GEN_PDF_RETRIES,
)
app.add_command(gen)


prepare = create_prepare_command(
    default_output_dir=DEFAULT_PREPARE_OUTPUT_DIR,
    default_jobspec_path=DEFAULT_JOBSPEC_PATH,
    prompts_dirname=PROMPT_TEMPLATE_DIRNAME,
    slide_inputs_filename=SLIDE_INPUTS_FILENAME,
)
app.add_command(prepare)

template = create_template_command(
    default_extract_output=DEFAULT_TEMPLATE_OUTPUT_DIR,
    default_release_output=DEFAULT_TEMPLATE_RELEASE_OUTPUT_DIR,
    default_mode=DEFAULT_TEMPLATE_LAYOUT_MODE,
)
app.add_command(template)
outline = create_outline_command(
    default_output_dir=DEFAULT_DRAFT_OUTPUT_DIR,
    default_appendix_limit=DEFAULT_APPENDIX_LIMIT,
    default_prepare_cards_path=DEFAULT_PREPARE_OUTPUT_DIR / PREPARE_CARD_FILENAME,
    default_draft_filename=DEFAULT_DRAFT_FILENAME,
    default_approved_filename=DEFAULT_APPROVED_FILENAME,
    default_draft_log_filename=DEFAULT_DRAFT_LOG_FILENAME,
    default_generate_ready_filename=DEFAULT_GENERATE_READY_FILENAME,
    default_generate_ready_meta_filename=DEFAULT_GENERATE_READY_META_FILENAME,
    default_draft_meta_filename=DEFAULT_DRAFT_META_FILENAME,
)
app.add_command(outline)


compose = create_compose_command(
    default_appendix_limit=DEFAULT_APPENDIX_LIMIT,
    default_output_dir=DEFAULT_COMPOSE_OUTPUT_DIR,
    default_rules_path=DEFAULT_RULES_PATH,
    default_prepare_cards_path=DEFAULT_PREPARE_OUTPUT_DIR / PREPARE_CARD_FILENAME,
    default_draft_filename=DEFAULT_DRAFT_FILENAME,
    default_approved_filename=DEFAULT_APPROVED_FILENAME,
    default_draft_log_filename=DEFAULT_DRAFT_LOG_FILENAME,
    default_draft_meta_filename=DEFAULT_DRAFT_META_FILENAME,
    default_generate_ready_filename=DEFAULT_GENERATE_READY_FILENAME,
    default_generate_ready_meta_filename=DEFAULT_GENERATE_READY_META_FILENAME,
)
app.add_command(compose)


mapping = create_mapping_command(
    default_output_dir=DEFAULT_GEN_OUTPUT_DIR,
    default_rules_path=DEFAULT_RULES_PATH,
    default_prepare_cards_path=DEFAULT_PREPARE_OUTPUT_DIR / PREPARE_CARD_FILENAME,
)
app.add_command(mapping)


tpl_extract = create_tpl_extract_command(
    default_output_dir=DEFAULT_TEMPLATE_OUTPUT_DIR,
    default_layout_mode=DEFAULT_TEMPLATE_LAYOUT_MODE,
)
app.add_command(tpl_extract)


layout_validate = create_layout_validate_command(
    default_output_dir=DEFAULT_VALIDATION_OUTPUT_DIR,
)
app.add_command(layout_validate)

edit = create_edit_command()
app.add_command(edit)


tpl_release = create_tpl_release_command(
    default_output_dir=DEFAULT_TEMPLATE_RELEASE_OUTPUT_DIR,
    default_layout_mode=DEFAULT_TEMPLATE_LAYOUT_MODE,
)
app.add_command(tpl_release)


if __name__ == "__main__":
    app()
