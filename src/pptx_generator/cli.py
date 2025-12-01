"""pptx_generator CLI."""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Optional

import click
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from .cli_handlers import (
    PROMPT_USER_SECTION_END,
    PROMPT_USER_SECTION_START,
    SLIDE_INPUTS_FILENAME,
    PrepareCommandConfig,
    PrepareCommandError,
    build_prompt_identifier,
    run_prepare_command,
    slugify_prompt_layout,
)
from .cli_handlers.common import (
    configure_file_logging,
    configure_llm_logger,
    determine_log_level,
    dump_json,
    log_current_llm_provider,
)
from .cli_handlers.compose import (
    ComposeCommandConfig,
    ComposeCommandError,
    run_compose_command,
)
from .cli_handlers.layout_validation import (
    LayoutValidateCommandConfig,
    LayoutValidateCommandError,
    echo_layout_validation_result,
    run_layout_validate_command,
)
from .cli_handlers.mapping import (
    MappingCommandConfig,
    MappingCommandError,
    echo_mapping_outputs,
    run_mapping_command,
)
from .draft_intel import load_return_reasons
from .models import JobSpec, SpecValidationError
from .pipeline import DraftStructuringOptions, PrepareNormalizationError
from .pipeline.draft_structuring import DraftStructuringError
from .settings import RulesConfig
from .cli_handlers.outline import (
    OutlineCommandConfig,
    run_outline_command,
)
from .cli_handlers.rendering import (
    GenerateCommandConfig,
    GenerateCommandError,
    echo_render_outputs,
    run_generate_command,
)
from .cli_handlers.template_commands import (
    TemplateCommandConfig,
    TemplateCommandError,
    TemplateExtractCommandConfig,
    TemplateReleaseCommandConfig,
    run_template_command,
    run_template_extract_command,
    run_template_release_command,
)
from .cli_handlers.template_extraction import (
    PROMPT_TEMPLATE_DIRNAME,
)
from .cli_handlers.template_release import echo_template_release_result, run_template_release

DEFAULT_RULES_PATH = Path("config/rules.json")
DEFAULT_CHAPTER_TEMPLATES_DIR = Path("config/chapter_templates")
DEFAULT_RETURN_REASONS_PATH = Path("config/return_reasons.json")
DEFAULT_PREPARE_POLICY_PATH = Path("config/prepare_policies/default.json")
DEFAULT_PREPARE_OUTPUT_DIR = Path(".pptx/prepare")
DEFAULT_JOBSPEC_PATH = Path(".pptx/extract/jobspec.json")

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
    output_dir: Path,
    jobspec: Path | None,
    mode: str,
    page_limit: int | None,
) -> PrepareCommandConfig:
    return PrepareCommandConfig(
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


load_dotenv()
@click.group(
    help="JSON 仕様から PPTX を生成する CLI",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("-v", "--verbose", is_flag=True, help="INFO レベルの冗長ログを出力する")
@click.option("--debug", is_flag=True, help="DEBUG レベルで詳細ログを出力する")
def app(verbose: bool, debug: bool) -> None:
    """CLI ルートエントリ。"""
    level, deferred_logs = determine_log_level(verbose, debug)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        force=True,
    )
    logging.getLogger("openai").setLevel(level)
    cli_logger = logging.getLogger("pptx_generator.cli")
    for message_level, message in deferred_logs:
        cli_logger.log(message_level, message)
    configure_llm_logger()
    configure_file_logging()


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

    config = GenerateCommandConfig(
        generate_ready_path=generate_ready_path,
        output_dir=output_dir,
        pptx_name=pptx_name,
        rules_path=rules,
        export_pdf=export_pdf,
        pdf_mode=pdf_mode,
        pdf_output=pdf_output,
        libreoffice_path=libreoffice_path,
        pdf_timeout=pdf_timeout,
        pdf_retries=pdf_retries,
        polisher_toggle=polisher_toggle,
        polisher_path=polisher_path,
        polisher_rules=polisher_rules,
        polisher_timeout=polisher_timeout,
        polisher_args=polisher_args,
        polisher_cwd=polisher_cwd,
        emit_structure_snapshot=emit_structure_snapshot,
    )
    try:
        result = run_generate_command(config)
    except GenerateCommandError as exc:
        message = str(exc)
        if message:
            click.echo(message, err=True)
        raise click.exceptions.Exit(code=exc.exit_code) from exc

    echo_render_outputs(result.context, result.audit_path)


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

    config = build_prepare_config(
        prepare_path=prepare_path,
        output_dir=output_dir,
        jobspec=jobspec,
        mode=mode,
        page_limit=page_limit,
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

    config = ComposeCommandConfig(
        spec_path=spec_path,
        draft_output=draft_output,
        target_length=target_length,
        structure_pattern=structure_pattern,
        appendix_limit=appendix_limit,
        chapter_templates_dir=chapter_templates_dir,
        chapter_template=chapter_template,
        analysis_summary_path=analysis_summary_path,
        show_layout_reasons=show_layout_reasons,
        output_dir=output_dir,
        rules_path=rules,
        prepare_cards=prepare_cards,
        draft_filename=DEFAULT_DRAFT_FILENAME,
        approved_filename=DEFAULT_APPROVED_FILENAME,
        log_filename=DEFAULT_DRAFT_LOG_FILENAME,
        meta_filename=DEFAULT_DRAFT_META_FILENAME,
        generate_ready_filename=DEFAULT_GENERATE_READY_FILENAME,
        generate_ready_meta_filename=DEFAULT_GENERATE_READY_META_FILENAME,
    )
    try:
        run_compose_command(config)
    except ComposeCommandError as exc:
        message = str(exc)
        if exc.errors:
            _echo_errors(message or "エラーが発生しました", exc.errors)
        elif message:
            click.echo(message, err=True)
        raise click.exceptions.Exit(code=exc.exit_code) from exc


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
    config = MappingCommandConfig(
        spec_path=spec_path,
        output_dir=output_dir,
        rules_path=rules,
        draft_output=draft_output,
        prepare_cards=prepare_cards,
    )

    try:
        result = run_mapping_command(config)
    except MappingCommandError as exc:
        message = str(exc)
        if exc.errors:
            _echo_errors(message or "エラーが発生しました", exc.errors)
        elif message:
            click.echo(message, err=True)
        raise click.exceptions.Exit(code=exc.exit_code) from exc

    echo_mapping_outputs(result.context)


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
    log_current_llm_provider("template")

    config = TemplateCommandConfig(
        template_path=template_path,
        output_dir=output,
        format=format,
        layout=layout,
        anchor=anchor,
        layout_mode=layout_mode,
        template_ai_policy=template_ai_policy,
        template_ai_policy_id=template_ai_policy_id,
        disable_template_ai=disable_template_ai,
        with_release=with_release,
        brand=brand,
        version=version,
        template_id=template_id,
        release_output=release_output,
        generated_by=generated_by,
        reviewed_by=reviewed_by,
        baseline_release=baseline_release,
        golden_specs=golden_specs,
        slide_snapshot=slide,
        force=force,
    )

    try:
        result = run_template_command(config)
    except TemplateCommandError as exc:
        message = str(exc)
        if message:
            click.echo(message, err=True)
        raise click.exceptions.Exit(code=exc.exit_code) from exc

    extraction_result = result.extraction
    validation_result = extraction_result.validation_result

    if extraction_result.prompt_templates_dir is not None:
        click.echo(f"プロンプト雛形を出力しました: {extraction_result.prompt_templates_dir}")
        if extraction_result.prompt_templates_created:
            click.echo(
                f"  -> {extraction_result.prompt_templates_created} 件のスライド雛形を生成しました。必要に応じて編集し、static prepare で反映してください。"
            )
        else:
            click.echo("  -> 既存の雛形を保持しました。変更があればファイルを手動で更新してください。")

    click.echo("テンプレ stage（抽出＋検証）が完了しました。")

    if not result.release:
        return

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
    config = TemplateExtractCommandConfig(
        template_path=template_path,
        output_dir=output_dir,
        format=format,
        layout=layout,
        anchor=anchor,
        layout_mode=layout_mode,
        template_ai_policy=template_ai_policy,
        template_ai_policy_id=template_ai_policy_id,
        disable_template_ai=disable_template_ai,
    )

    try:
        run_template_extract_command(config)
    except TemplateCommandError as exc:
        message = str(exc)
        if message:
            click.echo(message, err=True)
        raise click.exceptions.Exit(code=exc.exit_code) from exc


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

    config = LayoutValidateCommandConfig(
        template_path=template_path,
        output_dir=output_dir,
        template_id=template_id,
        baseline=baseline,
        analyzer_snapshot=analyzer_snapshot,
    )

    try:
        result = run_layout_validate_command(config)
    except LayoutValidateCommandError as exc:
        message = str(exc)
        if message:
            click.echo(message, err=True)
        raise click.exceptions.Exit(code=exc.exit_code) from exc

    echo_layout_validation_result(result)


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

    config = TemplateReleaseCommandConfig(
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
    try:
        result = run_template_release_command(config)
    except TemplateCommandError as exc:
        message = str(exc)
        if message:
            click.echo(message, err=True)
        raise click.exceptions.Exit(code=exc.exit_code) from exc

    echo_template_release_result(result)


def _echo_errors(message: str, errors: list[dict[str, object]] | None) -> None:
    click.echo(message, err=True)
    if not errors:
        return
    formatted = json.dumps(errors, ensure_ascii=False, indent=2)
    click.echo(formatted, err=True)


if __name__ == "__main__":
    app()
