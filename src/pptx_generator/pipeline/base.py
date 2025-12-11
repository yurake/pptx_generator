"""パイプライン共通の基盤クラス。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from ..config_manager import ResolvedConfig
from ..models import JobSpec

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """パイプライン内でのステージを表す。"""

    TEMPLATE = "template"
    PREPARE = "prepare"
    COMPOSE = "compose"
    MAPPING = "mapping"
    RENDER = "render"
    POST_PROCESS = "post_process"


@dataclass(slots=True)
class StageResult:
    """ステージ実行結果のメタ情報。"""

    stage: PipelineStage
    success: bool
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PipelineContext:
    """パイプライン全体で共有する情報。"""

    spec: JobSpec
    workdir: Path
    execution_id: str = field(default_factory=lambda: uuid4().hex)
    current_stage: PipelineStage | None = None
    config_snapshot: ResolvedConfig | None = None
    error_history: list[str] = field(default_factory=list)
    execution_trace: list[str] = field(default_factory=list)
    stage_results: list[StageResult] = field(default_factory=list)
    artifacts: dict[str, object] = field(default_factory=dict)

    def add_artifact(self, key: str, value: object) -> None:
        logger.debug("artifact 登録: %s", key)
        self.artifacts[key] = value

    def require_artifact(self, key: str) -> object:
        if key not in self.artifacts:
            msg = f"artifact '{key}' が存在しません"
            raise KeyError(msg)
        return self.artifacts[key]

    def advance_stage(self, stage: PipelineStage) -> None:
        self.current_stage = stage
        self.execution_trace.append(stage.value)

    def record_step(self, name: str) -> None:
        self.execution_trace.append(name)

    def record_error(self, message: str) -> None:
        self.error_history.append(message)

    def record_stage_result(self, result: StageResult) -> None:
        self.stage_results.append(result)


class PipelineStep(Protocol):
    """各処理ステップに共通するインターフェース。"""

    name: str

    def run(self, context: PipelineContext) -> None:
        ...


class StageContract(PipelineStep, Protocol):
    """ステージ契約を明示する基底。"""

    stage: PipelineStage

    def validate_input(self, context: PipelineContext) -> None:
        ...

    def execute(self, context: PipelineContext) -> StageResult | None:
        ...

    def run(self, context: PipelineContext) -> None:
        self.validate_input(context)
        result = self.execute(context)
        if isinstance(result, StageResult):
            context.record_stage_result(result)


class PipelineRunner:
    """ステップを順次実行するシンプルなランナー。"""

    def __init__(self, steps: list[PipelineStep]) -> None:
        self._steps = steps

    def execute(self, context: PipelineContext) -> None:
        for step in self._steps:
            logger.info("step 開始: %s", step.name)
            stage = getattr(step, "stage", None)
            if isinstance(stage, PipelineStage):
                context.advance_stage(stage)
            context.record_step(step.name)
            try:
                step.run(context)
            except Exception as exc:  # noqa: BLE001
                context.record_error(str(exc))
                raise
            logger.info("step 完了: %s", step.name)
