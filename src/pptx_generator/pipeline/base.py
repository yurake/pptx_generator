"""パイプライン共通の基盤クラス。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Iterator, MutableMapping, Protocol
from uuid import uuid4

from ..config_manager import ResolvedConfig
from ..models import JobSpec
from ..runtime.job_context import get_current_job
from ..logging import set_current_stage

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


class PipelineArtifactKey(str, Enum):
    """よく使うアーティファクトキーを列挙する。"""

    TEMPLATE_STYLE = "template_style"
    TEMPLATE_STYLE_DATA = "template_style_data"
    DRAFT_DOCUMENT = "draft_document"
    DRAFT_DOCUMENT_PATH = "draft_document_path"
    DRAFT_REVIEW_LOG = "draft_review_log"
    DRAFT_REVIEW_LOG_PATH = "draft_review_log_path"
    DRAFT_GENERATE_READY = "generate_ready"
    DRAFT_GENERATE_READY_META_PATH = "generate_ready_meta_path"
    PREPARE_DOCUMENT = "prepare_document"
    PREPARE_DOCUMENT_PATH = "prepare_document_path"
    GENERATE_READY = "generate_ready"
    GENERATE_READY_PATH = "generate_ready_path"
    MAPPING_LOG_PATH = "mapping_log_path"
    MAPPING_META = "mapping_meta"
    PIPELINE_TRACE_PATH = "pipeline_trace_path"


class PipelineArtifacts(MutableMapping[str, object]):
    """アーティファクトを型安全に扱う薄いラッパー。"""

    def __init__(self, initial: dict[str, object] | None = None) -> None:
        self._store: dict[str, object] = dict(initial or {})

    def __getitem__(self, key: str | PipelineArtifactKey) -> object:
        return self._store[self._key(key)]

    def __setitem__(self, key: str | PipelineArtifactKey, value: object) -> None:
        self._store[self._key(key)] = value

    def __delitem__(self, key: str | PipelineArtifactKey) -> None:
        del self._store[self._key(key)]

    def __iter__(self) -> Iterator[str]:
        return iter(self._store)

    def __len__(self) -> int:
        return len(self._store)

    def _key(self, key: str | PipelineArtifactKey) -> str:
        return key.value if isinstance(key, PipelineArtifactKey) else key

    # 互換メソッド
    def get(self, key: str | PipelineArtifactKey, default: object | None = None) -> object | None:  # type: ignore[override]
        return self._store.get(self._key(key), default)

    def setdefault(
        self,
        key: str | PipelineArtifactKey,
        default: object | None = None,
    ) -> object | None:  # type: ignore[override]
        return self._store.setdefault(self._key(key), default)

    def update(self, other: Iterable[tuple[str, object]] | dict[str, object], **kwargs: object) -> None:  # type: ignore[override]
        if isinstance(other, dict):
            items = other.items()
        else:
            items = other
        for key, value in items:
            self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    @classmethod
    def from_mapping(cls, mapping: MutableMapping[str, object]) -> "PipelineArtifacts":
        if isinstance(mapping, PipelineArtifacts):
            return mapping
        return cls(dict(mapping))

    def as_dict(self) -> dict[str, object]:
        return dict(self._store)


@dataclass(slots=True)
class PipelineContext:
    """パイプライン全体で共有する情報。"""

    spec: JobSpec
    workdir: Path
    job_id: str = field(default_factory=lambda: uuid4().hex)
    transaction_id: str = field(default_factory=lambda: uuid4().hex)
    current_stage: PipelineStage | None = None
    config_snapshot: ResolvedConfig | None = None
    error_history: list[str] = field(default_factory=list)
    execution_trace: list[str] = field(default_factory=list)
    stage_results: list[StageResult] = field(default_factory=list)
    artifacts: PipelineArtifacts = field(default_factory=PipelineArtifacts)

    def __post_init__(self) -> None:
        current_job = get_current_job()
        if current_job is not None:
            self.job_id = current_job.job_id
            self.transaction_id = current_job.transaction_id
        if not isinstance(self.artifacts, PipelineArtifacts):
            self.artifacts = PipelineArtifacts.from_mapping(self.artifacts)

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
        set_current_stage(stage.value)

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
            next_stage = getattr(step, "stage", None)
            stage_value = next_stage.value if isinstance(next_stage, PipelineStage) else getattr(
                context.current_stage, "value", None
            )
            logger.info(
                "step 開始: %s job_id=%s tx=%s stage=%s",
                step.name,
                context.job_id[:8],
                context.transaction_id[:8],
                stage_value,
            )
            stage = getattr(step, "stage", None)
            if isinstance(stage, PipelineStage):
                context.advance_stage(stage)
            context.record_step(step.name)
            try:
                step.run(context)
            except Exception as exc:  # noqa: BLE001
                context.record_error(str(exc))
                raise
            logger.info(
                "step 完了: %s job_id=%s tx=%s stage=%s",
                step.name,
                context.job_id[:8],
                context.transaction_id[:8],
                getattr(context.current_stage, "value", None),
            )
