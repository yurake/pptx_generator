"""パイプライン共通の基盤クラス。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ..models import JobSpec

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PipelineContext:
    """パイプライン全体で共有する情報。"""

    spec: JobSpec
    workdir: Path
    artifacts: dict[str, object] = field(default_factory=dict)

    def add_artifact(self, key: str, value: object) -> None:
        logger.debug("artifact 登録: %s", key)
        self.artifacts[key] = value

    def require_artifact(self, key: str) -> object:
        if key not in self.artifacts:
            msg = f"artifact '{key}' が存在しません"
            raise KeyError(msg)
        return self.artifacts[key]


class PipelineStep(Protocol):
    """各処理ステップに共通するインターフェース。"""

    name: str

    def run(self, context: PipelineContext) -> None:
        ...


class PipelineRunner:
    """ステップを順次実行するシンプルなランナー。"""

    def __init__(self, steps: list[PipelineStep]) -> None:
        self._steps = steps

    def execute(self, context: PipelineContext) -> None:
        for step in self._steps:
            logger.info("step 開始: %s", step.name)
            step.run(context)
            logger.info("step 完了: %s", step.name)
