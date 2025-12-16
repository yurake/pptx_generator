from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

import click

from pptx_generator.pipeline import (
    AnalyzerOptions,
    PipelineContext,
    PipelineRunner,
    RenderingOptions,
    SimpleAnalyzerStep,
    SimpleRefinerStep,
    SimpleRendererStep,
    SpecValidatorStep,
    TemplateExtractor,
    TemplateExtractorOptions,
)
from pptx_generator.pipeline.refiner import RefinerOptions
from pptx_generator.settings import RulesConfig
from pptx_generator.settings.loader import load_rules_config
from pptx_generator.settings.paths import get_default_config_path
from pptx_generator.template_audit import (
    build_release_report,
    build_template_release,
    load_template_release,
)
from pptx_generator.template_style import extract_template_style
from pptx_generator.models import (
    TemplateRelease,
    TemplateReleaseDiagnostics,
    TemplateReleaseGoldenRun,
    TemplateReleaseReport,
)

from .common import load_jobspec

logger = logging.getLogger(__name__)

DEFAULT_RULES_PATH = get_default_config_path("pipeline_rules.json")


@dataclass(slots=True)
class TemplateReleaseExecutionResult:
    release: TemplateRelease
    report: TemplateReleaseReport
    release_path: Path
    report_path: Path
    golden_runs_path: Path | None
    baseline_release: Path | None


def run_template_release(
    *,
    template_path: Path,
    brand: str,
    version: str,
    template_id: str | None,
    output_dir: Path,
    generated_by: str | None,
    reviewed_by: str | None,
    baseline_release: Path | None,
    golden_specs: Sequence[Path],
    layout_mode: str,
    rules_path: Path = DEFAULT_RULES_PATH,
) -> TemplateReleaseExecutionResult:
    resolved_template_id = resolve_template_id(template_id, brand, version)

    static_source = "slide" if layout_mode.lower() == "static" else "template"
    extractor = TemplateExtractor(
        TemplateExtractorOptions(
            template_path=template_path,
            layout_mode=layout_mode,
            static_source=static_source,
        )
    )
    spec = extractor.extract()

    output_dir.mkdir(parents=True, exist_ok=True)

    baseline = load_template_release(baseline_release) if baseline_release else None

    resolved_golden_specs, auto_golden_warnings = resolve_golden_specs(
        user_specs=list(golden_specs),
        baseline=baseline,
        baseline_release=baseline_release,
    )

    golden_runs: list[TemplateReleaseGoldenRun] = []
    golden_warnings: list[str] = []
    golden_errors: list[str] = []
    if resolved_golden_specs:
        golden_runs, golden_warnings, golden_errors = run_golden_specs(
            template_path=template_path,
            golden_specs=resolved_golden_specs,
            output_dir=output_dir,
            rules_path=rules_path,
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

    golden_runs_path: Path | None = None
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

    return TemplateReleaseExecutionResult(
        release=release,
        report=report,
        release_path=release_path,
        report_path=report_path,
        golden_runs_path=golden_runs_path,
        baseline_release=baseline_release,
    )


def echo_template_release_result(result: TemplateReleaseExecutionResult) -> None:
    click.echo(f"テンプレートリリースを出力しました: {result.release_path}")
    click.echo(f"リリースレポートを出力しました: {result.report_path}")
    if result.golden_runs_path is not None:
        click.echo(f"ゴールデンテスト結果を出力しました: {result.golden_runs_path}")
    if result.baseline_release is not None:
        click.echo(f"比較基準: {result.baseline_release}")
    print_diagnostics(result.release.diagnostics)


def run_golden_specs(
    *,
    template_path: Path,
    golden_specs: Sequence[Path],
    output_dir: Path,
    rules_path: Path = DEFAULT_RULES_PATH,
) -> tuple[list[TemplateReleaseGoldenRun], list[str], list[str]]:
    results: list[TemplateReleaseGoldenRun] = []
    warnings: list[str] = []
    errors: list[str] = []

    if not golden_specs:
        return results, warnings, errors

    rules_config = load_rules_config(rules_path)
    template_style = load_template_style_for_template(template_path, warnings)

    golden_root = output_dir / "golden_runs"

    for spec_path in golden_specs:
        run_dir = golden_root / spec_path.stem
        result = TemplateReleaseGoldenRun(
            spec_path=str(spec_path),
            status="passed",
            output_dir=str(run_dir),
        )

        try:
            spec = load_jobspec(spec_path)
        except Exception as exc:  # noqa: BLE001
            message = (
                f"golden spec {spec_path} の読み込みに失敗しました: {exc}"
            )
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
                template_style=template_style,
            )
        )
        refiner_bullet_level = (
            rules_config.max_bullet_level
            if rules_config.max_bullet_level is not None
            else RefinerOptions().max_bullet_level
        )
        refiner = SimpleRefinerStep(
            RefinerOptions(
                max_bullet_level=refiner_bullet_level,
            )
        )
        analyzer = SimpleAnalyzerStep(
            AnalyzerOptions(
                min_font_size=template_style.body_font.size_pt,
                default_font_size=template_style.body_font.size_pt,
                default_font_color=template_style.body_font.color_hex,
                preferred_text_color=template_style.colors.primary,
                background_color=template_style.colors.background,
                max_bullet_level=(
                    rules_config.max_bullet_level
                    if rules_config.max_bullet_level is not None
                    else AnalyzerOptions().max_bullet_level
                ),
                large_text_threshold_pt=template_style.body_font.size_pt,
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


def resolve_golden_specs(
    *,
    user_specs: Sequence[Path],
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

    if baseline is None or user_specs:
        return resolved, warnings

    base_dir = baseline_release.parent if baseline_release is not None else Path.cwd()
    for run in baseline.golden_runs:
        candidate = resolve_golden_spec_path(run.spec_path, base_dir)
        if candidate is None:
            warnings.append(
                f"baseline のゴールデンスペックを解決できませんでした: {run.spec_path}"
            )
            continue
        _add_spec(candidate)

    return resolved, warnings


def resolve_golden_spec_path(spec_path: str, base_dir: Path) -> Path | None:
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


def load_template_style_for_template(
    template_path: Path, warnings: list[str]
) -> TemplateStyle:
    style, artifact = extract_template_style(template_path)
    source = artifact.get("source", {}) if isinstance(artifact, dict) else {}
    if source.get("type") == "default":
        error = source.get("error")
        if error:
            warnings.append(
                f"テンプレートからスタイル情報を抽出できなかったため既定値を使用します: {error}"
            )
    return style


def resolve_template_id(template_id: Optional[str], brand: str, version: str) -> str:
    if template_id and template_id.strip():
        return template_id.strip()
    base = f"{brand}_{version}"
    return base.replace(" ", "_")


def print_diagnostics(diagnostics: TemplateReleaseDiagnostics) -> None:
    if diagnostics.warnings:
        click.echo(f"警告: {len(diagnostics.warnings)} 件", err=True)
        for warning in diagnostics.warnings:
            click.echo(f"  - {warning}", err=True)
    if diagnostics.errors:
        click.echo(f"エラー: {len(diagnostics.errors)} 件", err=True)
        for error in diagnostics.errors:
            click.echo(f"  - {error}", err=True)
