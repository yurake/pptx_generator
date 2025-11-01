"""生成AI用プロンプトのレジストリ。"""

from __future__ import annotations

from typing import Final


class PromptRegistryError(KeyError):
    """プロンプト ID が未定義の場合に発生する例外。"""


PROMPTS: Final[dict[str, str]] = {
    "content.baseline": (
        "次の情報をもとにスライド \"{slide_title}\" の本文候補を箇条書きで3点まとめてください。"
        "案件名: {spec_title} / クライアント: {spec_client}。"
    ),
    "content.cover": (
        "カバースライド \"{slide_title}\" のリード文を1行で生成してください。"
        "案件名: {spec_title}。"
    ),
    "content.summary": (
        "スライド \"{slide_title}\" の要約を3行以内で作成してください。"
        "読者が最初に理解すべきポイントを強調してください。"
    ),
}


def get_prompt_template(prompt_id: str) -> str:
    """登録済みプロンプト ID からテンプレート文字列を取得する。"""

    try:
        return PROMPTS[prompt_id]
    except KeyError as exc:
        msg = f"prompt_id '{prompt_id}' は登録されていません"
        raise PromptRegistryError(msg) from exc


def list_prompt_ids() -> tuple[str, ...]:
    """登録済みプロンプト ID の一覧を返す。"""

    return tuple(PROMPTS.keys())
