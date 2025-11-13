"""Prompt templates for brief generation."""

from __future__ import annotations

BRIEF_GENERATION_PROMPT = """
あなたは B2B 提案資料用の構成アシスタントです。以下の入力を読み取り、
章構成と各章に対応する BriefCard を JSON 形式で生成してください。

# 入力
{brief_payload}

# 出力フォーマット
JSON オブジェクトで返してください。キーは次のとおりです:
- chapters: BriefCard の配列。各要素は以下のプロパティを持ちます。
  - title: 章タイトル。
  - card_id: 一意な ID (英数字とハイフンのみ)。未指定の場合は title をスラグ化。
  - story_phase: introduction / problem / solution / impact / next のいずれか。
  - intent_tags: 章の意図を表す配列（例: ["introduction"]）。空の場合は story_phase を含める。
  - message: 章全体の要約（1 行程度）。
  - narrative: 箇条書き本文の配列。最大 6 行、各行 40 文字以内。
  - supporting_points: 補足情報の配列。各要素は { "statement": "...", "evidence": {"type": "...", "value": "..."} } 形式。
    evidence が不要なら省略してよい。

# 制約
- narrative の行数は 6 行以下とし、40 文字以内に収めてください。
- supporting_points が未入力で narrative だけの場合、 narrative と同じ内容を supporting_points に複製しても構いません。
- JSON 以外のテキストや説明文は含めないでください。
"""


def build_brief_prompt(payload: dict[str, object]) -> str:
    """Render the brief generation prompt with the given payload."""
    import json

    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    return BRIEF_GENERATION_PROMPT.replace("{brief_payload}", serialized, 1)
