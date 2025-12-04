"""テンプレートAI向けプロンプト生成ヘルパー。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict

from ..utils.usage_tags import CANONICAL_USAGE_TAGS

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from .client import TemplateAIRequest


TEMPLATE_SYSTEM_PROMPT = (
    "あなたは B2B プレゼン資料テンプレートを分析し、レイアウトの用途タグを判定するアシスタントです。"
    "必ず JSON オブジェクトのみで出力し、usage_tags に CANONICAL usage tags "
    f"({', '.join(sorted(CANONICAL_USAGE_TAGS))}) のみを含めてください。"
)


def build_system_prompt() -> str:
    """テンプレートAIへ渡すシステムプロンプトを返す。"""

    return TEMPLATE_SYSTEM_PROMPT


def build_user_prompt(request: "TemplateAIRequest") -> str:
    """テンプレートAI用のユーザープロンプトを構築する。"""

    payload: Dict[str, Any] = dict(request.payload)
    payload["instruction"] = request.prompt
    return json.dumps(payload, ensure_ascii=False, indent=2)
