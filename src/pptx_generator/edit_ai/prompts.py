from __future__ import annotations

import json
from typing import Iterable


SYSTEM_PROMPT = """あなたはプレゼン編集アシスタントです。以下のルールで JSON を返してください。
- 入力: shape_id とテキスト、スライド情報（必要ならスクリーンショットパス）
- 各要素について指示文が含まれているか判定し、必要なら書き換えた contents を返す
- 出力は JSON 配列のみ: [{"shape_id": number, "edit": true|false, "contents": string}]
- 余計なキーやテキストは出力しない
- edit=false のときは contents に元テキストをそのまま入れてよい
"""


def build_user_prompt(*, slide_title: str | None, shape_contexts: Iterable[dict[str, object]]) -> str:
    payload = {
        "slide_title": slide_title or "",
        "shapes": list(shape_contexts),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]
