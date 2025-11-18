"""Prompt templates for prepare generation."""

from __future__ import annotations

PREPARE_GENERATION_PROMPT = """
あなたは B2B 提案資料用の構成アシスタントです。提供される原稿 (raw_context) を読み取り、PowerPoint の 1 スライドに相当する PrepareCard を章ごとに生成してください。章数や順序は原稿の内容に基づき自由に決めて構いません。

# 入力
{prepare_payload}

# 出力フォーマット
JSON オブジェクトで返してください。トップレベルキーは chapters です。
- chapters: PrepareCard の配列。各要素は 1 スライド分の情報を表し、次のフィールドを含めてください。
  - card_id: スライド固有のスラグ ID（英数字とハイフンのみ）。story_phase と同じ文字列は避け、再生成時に安定する命名にしてください。
  - title: スライドタイトル。閲覧者にとって意味のある自然な文にしてください。
  - headline: そのページで最も伝えたい結論を 1 行で表現してください。
  - story_phase: slide の役割を表す値。introduction / problem / solution / impact / next など、文脈に適したフェーズ名を入れてください。
  - intent_tags: 章の意図を表す配列。空の場合は story_phase を含めてください。
  - body: 本文ブロックの配列。各ブロックは {"type": "paragraph"|"bullets"|"table"|..., "text": "...", "headers": [...], "rows": [[...]], "ref": "...", "description": "...", "data": {...}} のような構造を取り、必要な項目のみ出力してください。段落は 80 文字以内で簡潔にまとめてください。特殊スライドは type を "agenda" などに変えて表現しても構いません。
  - notes: ノート欄向けの補足配列。各要素は {"type": "note"|"rationale"|"risk"|..., "text": "..."} 形式で、本文の意図・根拠・追加説明を記述してください。空配列でも構いません。

- # 制約
- constraints.max_chapters が指定されている場合、出力する chapters 配列の要素数がその値を超えないようにする。
- story_phase / intent_tags は文脈に沿った値を選び、カードごとの役割が分かるようにする。
- headline はカード全体の結論を短く明示し、body には具体的な論点やデータを盛り込む。
- notes には本文では語りきれない補足、根拠、リスクなどを記述し、表に出さない前提情報をまとめる。
- JSON 以外のテキストや説明文は出力に含めない。
"""


def build_prepare_prompt(payload: dict[str, object]) -> str:
    """Render the prepare generation prompt with the given payload."""
    import json

    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    return PREPARE_GENERATION_PROMPT.replace("{prepare_payload}", serialized, 1)
