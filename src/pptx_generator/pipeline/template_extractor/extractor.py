"""High level TemplateExtractor facade."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ...models import JobSpecScaffold, TemplateSpec
from .options import TemplateExtractorOptions
from .step import TemplateExtractorStep

__all__ = ["TemplateExtractor"]


class TemplateExtractor:
    """スタンドアロンでテンプレート抽出を行うクラス。"""

    def __init__(self, options: TemplateExtractorOptions) -> None:
        self.options = options
        self.step = TemplateExtractorStep(options)

    def extract(self) -> TemplateSpec:
        """テンプレート抽出を実行してTemplateSpecを返す。"""
        return self.step.extract_template_spec()

    def build_jobspec_scaffold(
        self, template_spec: TemplateSpec, template_spec_path: Path | None = None
    ) -> JobSpecScaffold:
        """テンプレート仕様からジョブスペック雛形を構築する。"""
        resolved_path = str(template_spec_path) if template_spec_path else None
        return self.step.build_jobspec_scaffold(template_spec, resolved_path)

    def save_jobspec_scaffold(
        self, jobspec: JobSpecScaffold, output_path: Path
    ) -> None:
        """ジョブスペック雛形を保存する。"""
        self.step._save_jobspec_scaffold(jobspec, output_path)

    def extract_and_save(self, output_path: Optional[Path] = None) -> Path:
        """テンプレート抽出を実行してファイルに保存する。"""
        template_spec = self.extract()

        resolved_output = Path(output_path) if output_path is not None else None
        if resolved_output is None:
            if self.options.format == "yaml":
                resolved_output = Path("template_spec.yaml")
            else:
                resolved_output = Path("template_spec.json")

        jobspec_scaffold = self.build_jobspec_scaffold(template_spec, resolved_output)

        self.step._save_template_spec(template_spec, resolved_output)
        jobspec_path = self.step._determine_jobspec_path(resolved_output)
        self.step._save_jobspec_scaffold(jobspec_scaffold, jobspec_path)
        return resolved_output
