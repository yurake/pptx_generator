"""LLM クライアントで使用するデータモデル。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..models import JobSpec, Slide
from .policy import SlideAIPolicy


class LLMClient(Protocol):
    """生成 AI クライアント共通インターフェース。"""

    def generate(self, request: "AIGenerationRequest") -> "AIGenerationResponse":
        """リクエストに基づきスライド候補を生成する。"""

    def match_slide(self, request: "SlideMatchRequest") -> "SlideMatchResponse":
        """カードと JobSpec スライドの対応付けを推論する。"""


@dataclass(slots=True)
class AIGenerationRequest:
    """LLM へのリクエスト。"""

    prompt: str
    policy: SlideAIPolicy
    spec: JobSpec
    slide: Slide
    intent: str
    reference_text: str | None = None


@dataclass(slots=True)
class AIGenerationResponse:
    """LLM からの応答。"""

    title: str
    body: list[str] = field(default_factory=list)
    note: str | None = None
    intent: str | None = None
    model: str = "mock-local"
    warnings: list[str] = field(default_factory=list)
    raw_text: str | None = None


@dataclass(slots=True)
class SlideMatchCandidate:
    """スライド ID 整合の候補情報。"""

    slide_id: str
    title: str | None = None
    layout: str | None = None
    subtitle: str | None = None
    notes: str | None = None


@dataclass(slots=True)
class SlideMatchRequest:
    """スライド ID 整合用のリクエスト。"""

    card_id: str
    card_chapter: str | None
    card_intent: tuple[str, ...]
    card_story_phase: str | None
    card_summary: str
    prompt: str
    system_prompt: str
    candidates: list[SlideMatchCandidate]
    model: str | None = None


@dataclass(slots=True)
class SlideMatchResponse:
    """スライド ID 整合の応答。"""

    slide_id: str | None
    confidence: float
    reason: str | None
    model: str = "mock-local"
    warnings: list[str] = field(default_factory=list)
    raw_text: str | None = None


__all__ = [
    "AIGenerationRequest",
    "AIGenerationResponse",
    "SlideMatchCandidate",
    "SlideMatchRequest",
    "SlideMatchResponse",
    "LLMClient",
]
