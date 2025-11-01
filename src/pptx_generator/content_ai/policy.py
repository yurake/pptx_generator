"""AI ポリシー定義のロードと検証を提供する。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import logging

from pydantic import BaseModel, Field, ValidationError

from . import prompts


logger = logging.getLogger(__name__)

class ContentAIPolicyError(RuntimeError):
    """AI ポリシー定義に関する例外。"""


class ContentAISlidePolicy(BaseModel):
    """レイアウトごとの意図やプロンプト設定。"""

    layout: str | None = Field(
        default=None,
        description="対象となるレイアウト名。未指定の場合は全レイアウトに適用する。",
    )
    intent: str = Field(default="general", description="スライドの意図タグ。")
    prompt_id: str | None = Field(
        default=None,
        description="このレイアウト専用のプロンプト ID。",
    )
    prompt_template: str | None = Field(
        default=None,
        description="旧形式のテンプレート文字列。将来廃止予定。",
    )

    def resolve_prompt(self) -> str | None:
        """スライド単位のプロンプトテンプレートを取得する。"""

        if self.prompt_id:
            try:
                return prompts.get_prompt_template(self.prompt_id)
            except prompts.PromptRegistryError as exc:
                msg = f"スライド用 prompt_id '{self.prompt_id}' が未登録です"
                raise ContentAIPolicyError(msg) from exc
        return self.prompt_template


class ContentAIPolicy(BaseModel):
    """生成 AI 用のポリシー設定。"""

    id: str
    name: str
    description: str | None = None
    default_intent: str = Field(default="general")
    prompt_id: str | None = Field(
        default=None,
        description="ポリシー共通のプロンプト ID。",
    )
    prompt_template: str | None = Field(
        default=None,
        description="旧形式のテンプレート文字列。将来廃止予定。",
    )
    model: str = Field(default="mock-local")
    safeguards: dict[str, Any] = Field(default_factory=dict)
    slide_policies: list[ContentAISlidePolicy] = Field(default_factory=list)

    def resolve_intent(self, layout: str | None) -> str:
        """レイアウトに応じた意図タグを決定する。"""

        for entry in self.slide_policies:
            if entry.layout is None:
                continue
            if entry.layout == layout:
                return entry.intent
        return self.default_intent

    def resolve_prompt(self, layout: str | None) -> str:
        """レイアウトに応じたプロンプトテンプレートを返す。"""

        for entry in self.slide_policies:
            if entry.layout is None:
                continue
            if entry.layout == layout:
                candidate = entry.resolve_prompt()
                if candidate is not None:
                    return candidate
        return self._resolve_default_prompt()

    def _resolve_default_prompt(self) -> str:
        """ポリシー共通のプロンプトテンプレートを取得する。"""

        if self.prompt_id:
            try:
                return prompts.get_prompt_template(self.prompt_id)
            except prompts.PromptRegistryError as exc:
                msg = f"ポリシー {self.id} の prompt_id '{self.prompt_id}' が未登録です"
                raise ContentAIPolicyError(msg) from exc
        if self.prompt_template:
            return self.prompt_template
        msg = f"ポリシー {self.id} に prompt_id または prompt_template が設定されていません"
        raise ContentAIPolicyError(msg)


class ContentAIPolicySet(BaseModel):
    """ポリシー定義全体。"""

    version: str | None = None
    default_policy_id: str
    policies: list[ContentAIPolicy] = Field(default_factory=list)

    def get_policy(self, policy_id: str | None = None) -> ContentAIPolicy:
        """指定 ID のポリシーを返す。未指定時は default_policy_id を利用する。"""

        target_id = policy_id or self.default_policy_id
        for policy in self.policies:
            if policy.id == target_id:
                return policy
        msg = f"ポリシー ID '{target_id}' が定義ファイルに見つかりません"
        raise ContentAIPolicyError(msg)


def load_policy_set(path: Path) -> ContentAIPolicySet:
    """JSON ファイルからポリシー定義を読み込む。"""

    logger.info("Loading AI policy definition from %s", path.resolve())
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        msg = f"AI ポリシー定義ファイルが見つかりません: {path}"
        raise ContentAIPolicyError(msg) from exc
    except json.JSONDecodeError as exc:  # noqa: PERF203
        msg = f"AI ポリシー定義の JSON 解析に失敗しました: {path}"
        raise ContentAIPolicyError(msg) from exc

    try:
        policy_set = ContentAIPolicySet.model_validate(payload)
    except ValidationError as exc:
        msg = f"AI ポリシー定義の検証に失敗しました: {path}"
        raise ContentAIPolicyError(msg) from exc
    logger.info(
        "Loaded AI policy definition from %s (policies=%d)",
        path.resolve(),
        len(policy_set.policies),
    )
    return policy_set
