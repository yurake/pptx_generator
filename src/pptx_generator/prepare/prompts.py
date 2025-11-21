"""Prompt templates for prepare generation."""

from __future__ import annotations

PREPARE_DYNAMIC_PROMPT = """
あなたは B2B 提案資料用の構成アシスタントです。提供される原稿 (raw_context) を読み取り、PowerPoint の 1 スライドに相当する PrepareCard を章ごとに生成してください。章数や順序は原稿の内容に基づき自由に決めて構いません。

# 入力
{prepare_payload}

# 出力フォーマット
JSON オブジェクトで返してください。トップレベルキーは chapters です。
- chapters: PrepareCard の配列。各要素は 1 スライド分の情報を表し、次のフィールドを含めてください。
  - card_id: スライド固有のスラグ ID（英数字とハイフンのみ）。story_phase と同じ文字列は避け、再生成時に安定する命名にしてください。
  - title/headline: どちらか一方のみ使用します。通常スライドは `headline` を 1 行で記述し `title` は null にしてください。`options.include_title_page` が true の場合のみ先頭カードにデッキ全体の `title` を設定し、`headline` は null にします。
  - subtitle: 任意。章名やサブカテゴリを表す短いテキストを入れてください。章タイトルがあればここへ記載します。
  - story_phase: slide の役割を表す値。introduction / problem / solution / impact / next など、文脈に適したフェーズ名を入れてください。
  - intent_tags: 章の意図を表す配列。空の場合は story_phase を含めてください。
  - body: 本文ブロックの配列。各ブロックは {"type": "paragraph"|"bullets"|"table"|..., "text": "...", "headers": [...], "rows": [[...]], "ref": "...", "description": "...", "data": {...}} のような構造を取り、必要な項目のみ出力してください。段落は 80 文字以内で簡潔にまとめてください。特殊スライドは type を "agenda" などに変えて表現しても構いません。
  - notes: ノート欄向けの補足配列。各要素は {"type": "note"|"rationale"|"risk"|..., "text": "..."} 形式で、本文の意図・根拠・追加説明を記述してください。空配列でも構いません。

# 制約
- constraints.max_chapters が指定されている場合、出力する chapters 配列の要素数がその値を超えないようにする。
- options.include_title_page が true の場合は、先頭カードをタイトルページとして `title` のみ設定し、それ以外のカードは `headline` のみを設定する。false の場合は全カード `headline` のみとし、タイトルページを作成しない。
- story_phase / intent_tags は文脈に沿った値を選び、カードごとの役割が分かるようにする。
- headline はカード全体の結論を短く明示し、body には具体的な論点やデータを盛り込む。
- notes には本文では語りきれない補足、根拠、リスクなどを記述し、表に出さない前提情報をまとめる。
- JSON 以外のテキストや説明文は出力に含めない。
"""


PREPARE_STATIC_PROMPT = """
あなたは B2B 提案資料用の構成アシスタントです。提供される原稿 (raw_context) と Blueprint の slot 情報 (hints.slot) を読み取り、指定された 1 つの slot に差し込むための 1 スライド分の PrepareCard を生成してください。

# 入力
{prepare_payload}

# 出力フォーマット
JSON オブジェクトで返してください。トップレベルキーは chapters です。
- chapters: 要素数 1 の配列とし、その 1 要素が対象 slot 用のスライドを表します。
  - card_id: スライド固有のスラグ ID（英数字とハイフンのみ）。必ず安定した ID を生成してください。
  - title/headline: どちらか一方のみ使用します。通常は `headline` を 1 行で記述し `title` は null にしてください。
  - subtitle: 任意。章名や slot の役割を補足する短いテキストを入れてください。
  - story_phase: slide の役割を表す値。introduction / problem / solution / impact / next など、文脈に適したフェーズ名を入れてください。
  - intent_tags: 意図を表す配列。空の場合は story_phase を含めてください。hints.slot.intent_tags が与えられている場合はそれを優先し、足りない場合のみ story_phase を補います。
  - body: 本文ブロックの配列。各ブロックは {"type": "paragraph"|"bullets"|"table"|..., "text": "..."} のような構造を取り、slot に差し込みやすい短いテキストを中心に構成してください。
  - notes: ノート欄向けの補足配列。slot の意図や前提、読み上げる際のポイントなどを記述してください。空配列でも構いません。

# 制約
- 常に chapters の要素数は 1 とし、複数スライドを生成しないこと。
- hints.slot には Blueprint の slot 情報（slide_id, slot_id, anchor, content_type, required, intent_tags など）が含まれます。anchor や content_type に適した表現形式を選び、required=true の場合はプレゼンの骨格となる重要情報を優先してまとめてください。
- raw_context には対応する章のテキストや要約が含まれます。この内容を踏まえて、slot に収まるような簡潔な見出しと本文を生成してください。
- JSON 以外のテキストや説明文は出力に含めないでください。
"""


def build_prepare_prompt_dynamic(payload: dict[str, object]) -> str:
    """Render the prepare generation prompt for dynamic mode."""
    import json

    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    return PREPARE_DYNAMIC_PROMPT.replace("{prepare_payload}", serialized, 1)


def build_prepare_prompt_static(payload: dict[str, object]) -> str:
    """Render the prepare generation prompt for static mode."""
    import json

    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    return PREPARE_STATIC_PROMPT.replace("{prepare_payload}", serialized, 1)
