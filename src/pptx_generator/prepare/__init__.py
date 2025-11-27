"""Prepare 正規化モジュールの公開インターフェース。"""

from .models import (
    PrepareAIRecord,
    PrepareBodyBlock,
    PrepareCard,
    PrepareCardContent,
    PrepareCardRole,
    PrepareChapterDefinition,
    PrepareDocument,
    PrepareGenerationMeta,
    PrepareLogEntry,
    PrepareNoteEntry,
    PrepareStoryContext,
)
from .policy import (
    PreparePolicy,
    PreparePolicyError,
    PreparePolicySet,
    load_prepare_policy_set,
)
from .source import PrepareSourceChapter, PrepareSourceDocument, PrepareSourceMeta
from importlib import import_module
from typing import Any

_ORCHESTRATOR_MODULE = "pptx_generator.prepare_ai.orchestrator"


def _load_orchestrator() -> Any:
    return import_module(_ORCHESTRATOR_MODULE)


def __getattr__(name: str) -> Any:
    if name in {"PrepareAIOrchestrator", "PrepareAIOrchestrationError"}:
        module = _load_orchestrator()
        value = getattr(module, name)
        globals()[name] = value  # cache for subsequent attribute access
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    base = set(globals().keys())
    base.update({"PrepareAIOrchestrator", "PrepareAIOrchestrationError"})
    return sorted(base)

__all__ = [
    "PrepareAIRecord",
    "PrepareBodyBlock",
    "PrepareCard",
    "PrepareCardContent",
    "PrepareCardRole",
    "PrepareChapterDefinition",
    "PrepareDocument",
    "PrepareGenerationMeta",
    "PrepareLogEntry",
    "PrepareNoteEntry",
    "PreparePolicy",
    "PreparePolicyError",
    "PreparePolicySet",
    "PrepareSourceChapter",
    "PrepareSourceDocument",
    "PrepareSourceMeta",
    "PrepareStoryContext",
    "load_prepare_policy_set",
    "PrepareAIOrchestrator",
    "PrepareAIOrchestrationError",
]
