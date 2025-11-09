"""テンプレート usage_tags 推定用 AI ポリシー。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError


class TemplateAIPolicyError(RuntimeError):
    """テンプレート AI ポリシーの読み込みに失敗した場合の例外。"""


class TemplateAIStaticRule(BaseModel):
    """モック環境などで使用する静的タグ付与ルール。"""

    layout_name_pattern: str | None = Field(
        default=None, description="レイアウト名に適用する正規表現（省略時は任意）"
    )
    tags: list[str] = Field(default_factory=list, description="付与する usage_tags")

    def matches(self, layout_name: str) -> bool:
        if not self.layout_name_pattern:
            return True
        try:
            return re.search(self.layout_name_pattern, layout_name) is not None
        except re.error:
            return layout_name.casefold() == self.layout_name_pattern.casefold()


class TemplateAIPolicy(BaseModel):
    """テンプレート usage_tags 推定に使用するポリシー。"""

    id: str
    name: str
    description: str | None = None
    provider: str = Field(default="mock", description="LLM プロバイダ ID")
    model: str = Field(default="mock-template", description="利用するモデル名")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=16, le=16384)
    prompt_template: str | None = Field(
        default=None, description="テンプレート全体で利用するプロンプト"
    )
    static_rules: list[TemplateAIStaticRule] = Field(
        default_factory=list,
        description="モック時に利用する静的タグ付与ルール",
    )

    def resolve_prompt(self) -> str:
        if self.prompt_template:
            return self.prompt_template
        msg = "テンプレート AI 用プロンプトが定義されていません"
        raise TemplateAIPolicyError(msg)


class TemplateAIPolicySet(BaseModel):
    """テンプレート AI ポリシーのセット。"""

    version: str | None = None
    default_policy_id: str
    policies: list[TemplateAIPolicy] = Field(default_factory=list)

    def get_policy(self, policy_id: str | None = None) -> TemplateAIPolicy:
        target = policy_id or self.default_policy_id
        for policy in self.policies:
            if policy.id == target:
                return policy
        raise TemplateAIPolicyError(f"テンプレート AI ポリシー '{target}' が見つかりません")


def load_template_policy_set(path: Path) -> TemplateAIPolicySet:
    """JSON 定義からテンプレート AI ポリシーセットを読み込む。"""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        msg = f"テンプレート AI ポリシー定義が見つかりません: {path}"
        raise TemplateAIPolicyError(msg) from exc
    except json.JSONDecodeError as exc:
        msg = f"テンプレート AI ポリシー定義の解析に失敗しました: {path}"
        raise TemplateAIPolicyError(msg) from exc

    try:
        return TemplateAIPolicySet.model_validate(payload)
    except ValidationError as exc:
        msg = f"テンプレート AI ポリシー定義の検証に失敗しました: {path}"
        raise TemplateAIPolicyError(msg) from exc
