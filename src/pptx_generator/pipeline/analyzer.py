"""PPTX の簡易診断ステップ。"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from .base import PipelineContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AnalyzerOptions:
    output_filename: str = "analysis.json"


class SimpleAnalyzerStep:
    """現時点ではメタ情報のみを記録するダミー実装。"""

    name = "analyzer"

    def __init__(self, options: AnalyzerOptions | None = None) -> None:
        self.options = options or AnalyzerOptions()

    def run(self, context: PipelineContext) -> None:
        analysis = {
            "slides": len(context.spec.slides),
            "meta": context.spec.meta.model_dump(),
            "issues": [],
        }
        output_path = self._save(analysis, context.workdir)
        context.add_artifact("analysis_path", output_path)
        logger.info("analysis.json を出力しました: %s", output_path)

    def _save(self, payload: dict[str, object], workdir: Path) -> Path:
        output_dir = workdir / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / self.options.output_filename
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path
