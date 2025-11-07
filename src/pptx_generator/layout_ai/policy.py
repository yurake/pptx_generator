"""レイアウト推薦用 AI ポリシーの定義。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, Field, ValidationError


class LayoutAIPolicyError(RuntimeError):
    """レイアウト推薦ポリシーの読み込みに失敗した場合の例外。"""


class LayoutAISlidePolicy(BaseModel):
    """レイアウト単位のプロンプト設定。"""

    layout_id: str
    prompt_template: str
    allow_specialized: bool = False


class LayoutAIPolicy(BaseModel):
    """レイアウト推薦 AI 用のポリシー。"""

    id: str
    name: str
    description: str | None = None
    provider: str = Field(default="mock", description="LLM プロバイダ ID")
    model: str = Field(default="mock-layout", description="利用するモデル名")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=256, ge=16, le=4096)
    prompt_template: str | None = Field(default=None)
    slide_policies: list[LayoutAISlidePolicy] = Field(default_factory=list)

    def resolve_prompt(self, layout_id: str | None = None) -> str:
        if layout_id:
            for entry in self.slide_policies:
                if entry.layout_id == layout_id:
                    return entry.prompt_template
        if self.prompt_template:
            return self.prompt_template
        target = layout_id or "default"
        msg = f"layout_id={target} 用の prompt が定義されていません"
        raise LayoutAIPolicyError(msg)


class LayoutAIPolicySet(BaseModel):
    """ポリシー全体のコンテナ。"""

    version: str | None = None
    default_policy_id: str
    policies: list[LayoutAIPolicy] = Field(default_factory=list)

    def get_policy(self, policy_id: str | None = None) -> LayoutAIPolicy:
        target = policy_id or self.default_policy_id
        for policy in self.policies:
            if policy.id == target:
                return policy
        msg = f"レイアウト推薦ポリシー '{target}' が見つかりません"
        raise LayoutAIPolicyError(msg)


def load_layout_policy_set(path: Path) -> LayoutAIPolicySet:
    """JSON ファイルからポリシーセットを読み込む。"""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        msg = f"レイアウトAIポリシー定義が見つかりません: {path}"
        raise LayoutAIPolicyError(msg) from exc
    except json.JSONDecodeError as exc:
        msg = f"レイアウトAIポリシー定義の解析に失敗しました: {path}"
        raise LayoutAIPolicyError(msg) from exc

    try:
        return LayoutAIPolicySet.model_validate(payload)
    except ValidationError as exc:
        msg = f"レイアウトAIポリシー定義の検証に失敗しました: {path}"
        raise LayoutAIPolicyError(msg) from exc
