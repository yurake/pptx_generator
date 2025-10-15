"""pptx_generator CLI."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click

from .branding_extractor import (
    BrandingExtractionError,
    extract_branding_config,
)
from .models import (JobSpec, SpecValidationError, TemplateReleaseDiagnostics,
                     TemplateReleaseGoldenRun)
from .pipeline import (AnalyzerOptions, PdfExportError, PdfExportOptions,
                       PdfExportStep, PipelineContext, PipelineRunner,
                       RefinerOptions, RenderingOptions, SimpleAnalyzerStep,
                       SimpleRefinerStep, SimpleRendererStep, SpecValidatorStep,
                       TemplateExtractor, TemplateExtractorOptions)
from .template_audit import (build_release_report, build_template_release,
                             load_template_release)
from .settings import BrandingConfig, RulesConfig

DEFAULT_RULES_PATH = Path("config/rules.json")
DEFAULT_BRANDING_PATH = Path("config/branding.json")


@click.group(help="JSON 仕様から PPTX を生成する CLI")
@click.option("-v", "--verbose", is_flag=True, help="冗長ログを出力する")
def app(verbose: bool) -> None:
    """CLI ルートエントリ。"""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level, format="%(asctime)s %(levelname)s %(name)s - %(message)s")


@app.command("gen")
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
    help="生成物を保存するディレクトリ",
)
@click.option(
    "--template",
    "-t",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
    default=None,
    help="PPTX テンプレートファイル",
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
    "--branding",
    type=click.Path(exists=True, dir_okay=False,
                    readable=True, path_type=Path),
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
def gen(
    spec_path: Path,
    output_dir: Path,
    template: Optional[Path],
    pptx_name: str,
    rules: Path,
    branding: Optional[Path],
    export_pdf: bool,
    pdf_mode: str,
    pdf_output: str,
    libreoffice_path: Optional[Path],
    pdf_timeout: int,
    pdf_retries: int,
) -> None:
    """JSON 仕様から PPTX を生成する。"""
    try:
        spec = JobSpec.parse_file(spec_path)
    except SpecValidationError as exc:
        _echo_errors("スキーマ検証に失敗しました", exc.errors)
        raise click.exceptions.Exit(code=2) from exc

    rules_config = RulesConfig.load(rules)

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

    output_dir.mkdir(parents=True, exist_ok=True)
    context = PipelineContext(spec=spec, workdir=output_dir)

    branding_artifact = {"source": branding_source}
    if branding_payload is not None:
        branding_artifact["config"] = branding_payload
    context.add_artifact("branding", branding_artifact)

    renderer = SimpleRendererStep(
        RenderingOptions(
            template_path=template,
            output_filename=pptx_name,
            branding=branding_config,
        )
    )
    analyzer_rules = rules_config.analyzer
    refiner_rules = rules_config.refiner
    analyzer_defaults = AnalyzerOptions()
    body_font_size = branding_config.body_font.size_pt
    body_font_color = branding_config.body_font.color_hex
    primary_color = branding_config.primary_color
    background_color = branding_config.background_color

    analyzer = SimpleAnalyzerStep(
        AnalyzerOptions(
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
        )
    )
    refiner = SimpleRefinerStep(
        RefinerOptions(
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
    )
    if not export_pdf and pdf_mode != "both":
        click.echo("--pdf-mode は --export-pdf と併用してください", err=True)
        raise click.exceptions.Exit(code=2)

    pdf_options = PdfExportOptions(
        enabled=export_pdf,
        mode=pdf_mode,
        output_filename=pdf_output,
        soffice_path=libreoffice_path,
        timeout_sec=pdf_timeout,
        max_retries=pdf_retries,
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
    if pdf_options.enabled:
        steps.append(PdfExportStep(pdf_options))
    runner = PipelineRunner(steps)

    try:
        runner.execute(context)
    except SpecValidationError as exc:
        _echo_errors("業務ルール検証に失敗しました", exc.errors)
        raise click.exceptions.Exit(code=3) from exc
    except BrandingExtractionError as exc:
        click.echo(f"ブランド設定の抽出に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except FileNotFoundError as exc:
        click.echo(f"ファイルが見つかりません: {exc}", err=True)
        raise click.exceptions.Exit(code=4) from exc
    except PdfExportError as exc:
        click.echo(f"PDF 出力に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=5) from exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("パイプライン実行中にエラーが発生しました")
        raise click.exceptions.Exit(code=1) from exc

    audit_path = _write_audit_log(context)

    pptx_path = context.artifacts.get("pptx_path")
    analysis_path = context.artifacts.get("analysis_path")
    if pptx_path is not None:
        click.echo(f"PPTX: {pptx_path}")
    else:
        click.echo("PPTX: --pdf-mode=only のため保存しませんでした")
    click.echo(f"Analysis: {analysis_path}")
    pdf_path = context.artifacts.get("pdf_path")
    if pdf_path is not None:
        click.echo(f"PDF: {pdf_path}")
    click.echo(f"Audit: {audit_path}")


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
        branding_result = extract_branding_config(template_path)
        
        # 出力パス決定
        if format.lower() == "yaml":
            spec_path = output_dir / "template_spec.yaml"
        else:
            spec_path = output_dir / "template_spec.json"
        branding_output_path = output_dir / "branding.json"
        
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

        branding_payload = branding_result.to_branding_payload()
        branding_text = json.dumps(branding_payload, ensure_ascii=False, indent=2)
        branding_output_path.write_text(branding_text, encoding="utf-8")

        # 結果表示
        click.echo(f"テンプレート抽出が完了しました: {spec_path}")
        click.echo(f"ブランド設定を出力しました: {branding_output_path}")
        click.echo(f"抽出されたレイアウト数: {len(template_spec.layouts)}")
        
        total_anchors = sum(len(layout.anchors) for layout in template_spec.layouts)
        click.echo(f"抽出された図形・アンカー数: {total_anchors}")
        
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
    except Exception as exc:  # noqa: BLE001
        logging.exception("テンプレート抽出中にエラーが発生しました")
        click.echo(f"テンプレート抽出に失敗しました: {exc}", err=True)
        raise click.exceptions.Exit(code=1) from exc


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

        golden_runs: list[TemplateReleaseGoldenRun] = []
        golden_warnings: list[str] = []
        golden_errors: list[str] = []
        if golden_specs:
            golden_runs, golden_warnings, golden_errors = _run_golden_specs(
                template_path=template_path,
                golden_specs=list(golden_specs),
                output_dir=output_dir,
            )

        release = build_template_release(
            template_path=template_path,
            spec=spec,
            template_id=resolved_template_id,
            brand=brand,
            version=version,
            generated_by=generated_by,
            reviewed_by=reviewed_by,
            golden_runs=golden_runs,
            extra_warnings=golden_warnings,
            extra_errors=golden_errors,
        )
        release_path = output_dir / "template_release.json"
        release_path.write_text(
            json.dumps(release.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

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

        baseline = None
        if baseline_release is not None:
            baseline = load_template_release(baseline_release)

        report = build_release_report(current=release, baseline=baseline)
        report_path = output_dir / "release_report.json"
        report_path.write_text(
            json.dumps(report.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

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
            spec = JobSpec.parse_file(spec_path)
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


def _write_audit_log(context: PipelineContext) -> Path:
    outputs_dir = context.workdir
    outputs_dir.mkdir(parents=True, exist_ok=True)
    audit_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec_meta": context.spec.meta.model_dump(),
        "slides": len(context.spec.slides),
        "artifacts": {
            "pptx": _artifact_str(context.artifacts.get("pptx_path")),
            "analysis": _artifact_str(context.artifacts.get("analysis_path")),
            "pdf": _artifact_str(context.artifacts.get("pdf_path")),
        },
        "pdf_export": context.artifacts.get("pdf_export_metadata"),
        "refiner_adjustments": context.artifacts.get("refiner_adjustments"),
        "branding": context.artifacts.get("branding"),
    }
    audit_path = outputs_dir / "audit_log.json"
    audit_path.write_text(json.dumps(
        audit_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    context.add_artifact("audit_path", audit_path)
    return audit_path


def _artifact_str(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)


if __name__ == "__main__":
    app()
