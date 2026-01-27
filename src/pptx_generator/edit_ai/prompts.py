from __future__ import annotations

import json
from typing import Iterable


SYSTEM_PROMPT = """あなたはプレゼン編集アシスタントです。以下のルールで JSON を返してください。
- 入力: shape_id とテキスト、スライド情報（必要ならスクリーンショットと座標）
- 各要素について指示文が含まれているか判定し、必要なら書き換えた contents を返す
- 出力は JSON 配列のみ: [{"shape_id": number, "edit": true|false, "contents": string}]
- 余計なキーやテキストは出力しない
- edit=false のときは contents に元テキストをそのまま入れてよい
- 箇条書きは元の構造をできるだけ保つ（改行・リスト記号を維持）
- 会社名や固有名詞は改変しない
"""


def build_user_prompt(
    *,
    slide_title: str | None,
    shape_contexts: Iterable[dict[str, object]],
    slide_index: int | None = None,
    slide_size_in: dict[str, float] | None = None,
    screenshot: dict[str, object] | None = None,
) -> str:
    payload = {"slide_title": slide_title or "", "shapes": list(shape_contexts)}
    if slide_index is not None:
        payload["slide_index"] = slide_index
    if slide_size_in is not None:
        payload["slide_size_in"] = slide_size_in
    if screenshot is not None:
        payload["screenshot"] = screenshot
    return json.dumps(payload, ensure_ascii=False, indent=2)


__all__ = ["SYSTEM_PROMPT", "build_user_prompt"]
