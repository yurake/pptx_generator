"""生成 AI クライアントの抽象化とモック実装。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..models import JobSpec, Slide
from .policy import ContentAIPolicy

MAX_BODY_LINES = 6
MAX_BODY_LENGTH = 40
MAX_TITLE_LENGTH = 120


@dataclass(slots=True)
class AIGenerationRequest:
    """LLM へのリクエスト。"""

    prompt: str
    policy: ContentAIPolicy
    spec: JobSpec
    slide: Slide
    intent: str


@dataclass(slots=True)
class AIGenerationResponse:
    """LLM からの応答。"""

    title: str
    body: list[str] = field(default_factory=list)
    note: str | None = None
    intent: str | None = None
    model: str = "mock-local"
    warnings: list[str] = field(default_factory=list)


class LLMClient(Protocol):
    """生成 AI クライアント共通インターフェース。"""

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        """リクエストに基づきスライド候補を生成する。"""


class MockLLMClient:
    """開発用のモック LLM クライアント。"""

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        slide = request.slide
        title_source = slide.title or f"{request.spec.meta.title} ({slide.id})"
        title = _truncate(title_source, MAX_TITLE_LENGTH)

        bullet_texts: list[str] = []
        for group in slide.iter_bullet_groups():
            for item in group.items:
                bullet_texts.append(item.text)

        if not bullet_texts:
            bullet_texts.append(request.prompt)

        body, warnings = _normalize_body(bullet_texts)
        note = (
            f"{request.policy.name} ポリシーを使用して自動生成しました。"
            if request.policy.name
            else None
        )

        return AIGenerationResponse(
            title=title,
            body=body,
            note=note,
            intent=request.intent,
            model=request.policy.model,
            warnings=warnings,
        )


def _truncate(value: str, max_length: int) -> str:
    normalized = value.strip()
    if len(normalized) <= max_length:
        return normalized
    ellipsis = "..."
    if max_length <= len(ellipsis):
        return ellipsis[:max_length]
    return normalized[: max_length - len(ellipsis)] + ellipsis


def _normalize_body(candidates: list[str]) -> tuple[list[str], list[str]]:
    """本文候補を正規化し、長さ制限を満たすように整形する。"""

    body_lines: list[str] = []
    warnings: list[str] = []

    for candidate in candidates:
        text = candidate.strip()
        if not text:
            continue
        if len(body_lines) >= MAX_BODY_LINES:
            warnings.append("body_lines_truncated")
            break
        if len(text) > MAX_BODY_LENGTH:
            warnings.append("body_line_length_truncated")
            text = text[:MAX_BODY_LENGTH]
        body_lines.append(text)

    if not body_lines:
        body_lines.append("自動生成コンテンツ")

    return body_lines, warnings
