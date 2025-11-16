"""Prompt templates for brief generation."""

from __future__ import annotations

BRIEF_GENERATION_PROMPT = """
あなたは B2B 提案資料用の構成アシスタントです。提供される原稿 (raw_context) を読み取り、PowerPoint の 1 スライドに相当する BriefCard を章ごとに生成してください。章数や順序は原稿の内容に基づき自由に決めて構いません。

# 入力
{brief_payload}

# 出力フォーマット
JSON オブジェクトで返してください。トップレベルキーは chapters です。
- chapters: BriefCard の配列。各要素は 1 スライド分の情報を表し、次のフィールドを含めてください。
  - card_id: スライド固有のスラグ ID（英数字とハイフンのみ）。story_phase と同じ文字列は避けてください。
  - title: スライドタイトル。閲覧者にとって意味のある自然な文にしてください。
  - story_phase: slide の役割を表す値。introduction / problem / solution / impact / next など、文脈に適したフェーズ名を入れてください。
  - intent_tags: 章の意図を表す配列。空の場合は story_phase を含めてください。
  - message: スライド全体の要約（1 行程度）。
  - body: スライド本文の配列。本文は箇条書き・段落・表など自由な形式ですが、各要素は 40 文字以内のテキストで表現してください。
  - supporting_points: 補足情報の配列。各要素は {"statement": "...", "evidence": {"type": "...", "value": "..."}} 形式。evidence が不要な場合は省略可。

# 制約
- constraints.max_chapters が指定されている場合、その数を超えないよう章を構成する。
- story_phase / intent_tags は文脈に沿った値を選び、カードごとの役割が分かるようにする。
- narrative・supporting_points は原稿の内容を要約した具体的な文を入れる。
- JSON 以外のテキストや説明文は出力に含めない。
"""


def build_brief_prompt(payload: dict[str, object]) -> str:
    """Render the brief generation prompt with the given payload."""
    import json

    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    return BRIEF_GENERATION_PROMPT.replace("{brief_payload}", serialized, 1)
