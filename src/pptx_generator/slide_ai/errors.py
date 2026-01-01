"\"\"\"slide_ai 共通の例外定義。\"\"\""

from __future__ import annotations


class LLMClientConfigurationError(RuntimeError):
    """LLM クライアントの初期化に失敗した場合の例外。"""


__all__ = ["LLMClientConfigurationError"]
