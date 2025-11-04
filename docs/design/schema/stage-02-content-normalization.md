# コンテンツ準備スキーマ

工程2（コンテンツ準備）で生成される Brief 成果物の JSON 仕様を定義する。

## ファイル
- `prepare_card.json`: BriefCard コレクション。工程3のドラフト構築・マッピングの基礎データ。
- `brief_log.json`: ブリーフ承認イベントの監査ログ（初期状態は空配列）。
- `brief_ai_log.json`: 生成 AI との対話ログとワーニング情報。
- `ai_generation_meta.json`: ポリシー ID、生成統計、入力ハッシュなどのメタ情報。
- `brief_story_outline.json`: 章構成とカード ID の対応表。
- `audit_log.json`: 工程2全体の監査メタ。成果物パスと統計をまとめる。

## prepare_card.json
```jsonc
{
  "brief_id": "sample_import_content_summary",
  "cards": [
    {
      "card_id": "intro",
      "chapter": "イントロダクション",
      "message": "intro 現状と課題",
      "narrative": [
        "intro 現状と課題"
      ],
      "supporting_points": [
        {"statement": "営業リードタイムが平均 12 日で業界平均より 1.5 倍長い。"}
      ],
      "story": {"phase": "introduction"},
      "intent_tags": ["introduction"],
      "status": "draft",
      "autofix_applied": []
    }
  ]
}
```

### フィールド補足
- `card_id`: 工程3で参照するユニーク ID。
- `chapter`: 章タイトル。`brief_story_outline.json` の `chapters[].title` と整合させる。
- `story.phase`: ストーリーライン分類（`introduction` / `problem` / `solution` / `impact` など）。
- `intent_tags`: マッピング時の layout_hint / intent 推定に利用するタグ。
- `status`: `draft` / `approved` / `returned`。初期値は `draft`。
- `autofix_applied`: 生成 AI が提案した AutoFix の適用履歴。

## brief_ai_log.json
```jsonc
[
  {
    "card_id": "intro",
    "prompt_template": "brief.default",
    "model": "gpt-4o-mini",
    "response_digest": "intro 現状と課題",
    "warnings": ["token_limit"],
    "tokens": {"prompt": 512, "completion": 128, "total": 640},
    "generated_at": "2025-11-02T15:04:21.326381Z"
  }
]
```

- `warnings`: 生成時の注意事項。`llm_stub` / `token_limit` / `safety_blocked` などを想定。
- `tokens`: プロバイダーが返すトークン使用量。mock モードでは 0。

## ai_generation_meta.json
```jsonc
{
  "brief_id": "sample_import_content_summary",
  "generated_at": "2025-11-02T15:04:21.325659Z",
  "policy_id": "brief-default",
  "input_hash": "sha256:...",
  "cards": [
    {"card_id": "intro", "intent_tags": ["introduction"], "story_phase": "introduction", "content_hash": "sha256:...", "body_lines": 1}
  ],
  "statistics": {"cards_total": 4, "approved": 0, "returned": 0}
}
```

- `content_hash`: `cards[].narrative` / `supporting_points` をもとにしたハッシュ。工程3で差分検知に利用。
- `statistics`: 承認状態ごとの件数集計。

## brief_story_outline.json
```jsonc
{
  "brief_id": "sample_import_content_summary",
  "chapters": [
    {"id": "intro", "title": "イントロダクション", "cards": ["intro"]}
  ],
  "narrative_theme": null,
  "summary": null
}
```

- `chapters[].cards`: 章に紐づく `card_id` の配列。工程3で章順を初期化する。
- `narrative_theme` / `summary`: オプション項目。HITL で補完可能。

## audit_log.json
```jsonc
{
  "brief_normalization": {
    "generated_at": "2025-11-02T15:04:21.325659+00:00",
    "policy_id": "brief-default",
    "input_hash": "sha256:...",
    "outputs": {
      "prepare_card": "/path/to/prepare_card.json",
      "brief_log": "/path/to/brief_log.json",
      "brief_ai_log": "/path/to/brief_ai_log.json",
      "ai_generation_meta": "/path/to/ai_generation_meta.json",
      "brief_story_outline": "/path/to/brief_story_outline.json"
    },
    "statistics": {
      "cards_total": 4,
      "approved": 0,
      "returned": 0
    }
  }
}
```

- 監査ログは全成果物の絶対パスとハッシュ（将来拡張）を記録する。工程3・4 の `audit_log.json` と同様、`hashes` セクション追加を想定。

## バリデーション
- `prepare_card.json` の `cards[].card_id` は一意であること。
- `brief_story_outline.json` の `chapters[].cards` が `prepare_card.json` に収載されていること。
- `ai_generation_meta.json` の `cards[].card_id` が `prepare_card.json` と一致すること。
- `audit_log.json` の `outputs` パスは実際に生成された成果物を指すこと。

## サンプル
- `samples/brief/prepare_card.json`
- `samples/brief/brief_ai_log.json`
- `samples/brief/ai_generation_meta.json`
- `samples/brief/brief_story_outline.json`
- `samples/brief/audit_log.json`
