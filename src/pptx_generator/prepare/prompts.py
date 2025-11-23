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
  - body: 本文ブロックの配列。各ブロックはスライド要素に合わせて `type` を指定し、以下のフォーマットに従って構造化してください。
    - paragraph: `{"type": "paragraph", "text": "..."}` を出力し、text は 1 行 80 文字以内の要約にする。
    - bullets: `{"type": "bullets", "items": [...]}` を用い、`items` には各行のテキストを文字列配列で並べる（例: `["要点A", "要点B"]`）。ネストが必要な場合は `"  "` などのプレフィックスで表現してよい。互換用に `text` を添える場合でも `items` を必ず埋め、`text` は省略または空文字にする。
    - table: `{"type": "table", "headers": [...], "rows": [[...]]}` とし、Markdown ではなく配列で表データを返す。
    - その他の type: `{"type": "<custom>", "text": "...", "description": "...(任意)", "data": {...}}` のように必要なフィールドのみ埋め、アンカー指定が必要な場合は `ref` を設定する。
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
あなたは B2B 提案資料用の構成アシスタントです。提供される原稿 (raw_context) と Blueprint のスライド情報 (blueprint_slide) および slot 一覧 (slot_specs) を読み取り、スライド全体のコンテンツを 1 度で設計してください。出力は JSON オブジェクトで、各 slot ごとの差し込み内容を `slots` 配列にまとめてください。

# 入力
{prepare_payload}

# 出力フォーマット
JSON オブジェクトで返してください。トップレベルキーは `slots` です。
- slots: `slot_specs[*].slot_id` と一致するオブジェクトの配列。各要素は次のフィールドを含みます。
  - slot_id: 必須。入力の slot_specs[*].slot_id と一致させる。
  - title: 任意。タイトルが要求される slot の場合のみ設定する。通常は null。
  - headline: 任意。スライドの結論を 1 行でまとめる。title を併用する場合は headline を null にする。
  - subtitle: 任意。補助的な短いテキスト。
  - body: 本文ブロックの配列。各ブロックは slot の `content_type` に合わせて `type` を指定し、以下のフォーマットに従って構造化する。
    - paragraph: `{"type": "paragraph", "text": "..."}`。text は 1 行 80 文字以内の要約にまとめる。
    - bullets: `{"type": "bullets", "items": [...]}`。`items` には各行のテキストを文字列配列で並べる（例: `["要点A", "要点B"]`）。ネストが必要な場合は `"  "` などのプレフィックスで表現してよい。互換用に `text` を添える場合でも `items` を必ず埋め、`text` は省略または空文字にする。
    - table: `{"type": "table", "headers": [...], "rows": [[...]]}`。Markdown ではなく配列で表データを返す。
    - その他の type: `{"type": "<custom>", "text": "...", "description": "...(任意)", "data": {...}}` のように、slot の属性や anchor に合わせて必要なフィールドのみ設定する。アンカー指定が必要な場合は `ref` を設定する。
  - notes: ノート欄向けの補足配列。各要素は {"type": "note"|"rationale"|"risk"|..., "text": "..."} 形式。空配列でも可。

# 制約
- slot_specs[*] には slot ごとの anchor / required / intent_tags / content_type / context が含まれます。context を踏まえつつ、required=true の場合は必ず意味のあるテキストを生成してください。
- 同一スライド内での整合性を保つため、headline や body のトーンは raw_context の要約と一致させること。
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
