# マッピングスキーマ

工程5（マッピング）で利用する JSON 仕様を定義する。

## ファイル
- `rendering_ready.json`: レンダリングに必要なレイアウト決定済みデータ。
- `mapping_log.json`: 候補スコア、フォールバック、AI 補完履歴のログ。
- `fallback_report.json`: 収容不能など重大フォールバックの詳細（任意）。

## rendering_ready.json
```jsonc
{
  "slides": [
    {
      "layout_id": "overview__one_col_v1",
      "elements": {
        "title": "市場環境の変化",
        "body": ["国内需要は前年比12%増", "海外市場は横ばい"],
        "table_data": { "headers": ["項目", "数値"], "rows": [["売上", "112%"]] },
        "note": "為替前提は110円/ドル"
      },
      "meta": {
        "section": "市場概況",
        "page_no": 2,
        "sources": ["s01"],
        "fallback": "none"
      }
    }
  ],
  "meta": {
    "template_version": "acme_v1",
    "content_hash": "sha256:...",
    "generated_at": "2025-10-11T12:05:00+09:00"
  }
}
```

## mapping_log.json
```jsonc
{
  "slides": [
    {
      "ref_id": "s01",
      "selected_layout": "overview__one_col_v1",
      "candidates": [
        {"layout_id": "overview__one_col_v1", "score": 0.92},
        {"layout_id": "overview__two_col_v1", "score": 0.78}
      ],
      "fallback": {
        "applied": false,
        "history": []
      },
      "ai_patch": [
        {"patch_id": "p03", "description": "本文を45文字以内に要約"}
      ],
      "warnings": []
    }
  ],
  "meta": {
    "mapping_time_ms": 845,
    "fallback_count": 0,
    "ai_patch_count": 1
  }
}
```

### フィールド補足
- `elements` はテンプレ PH 名をキーにした構造。Renderer が直接利用する。
- `meta.sources`: 元コンテンツ (`content_approved`) の `slide_id` リスト。
- `fallback.history`: `["shrink_text", "split_slide"]` のように適用順を記録。
- `ai_patch`: 適用された JSON Patch の ID と説明。差分は別途ログに記録。
- `warnings`: `layout_mismatch`, `table_overflow` など Renderer へ引き継ぐ警告。

## サンプル
- `samples/rendering_ready.jsonc`
- `samples/mapping_log.jsonc`

## バリデーション
- `layout_id` がテンプレ構造 (`layouts.jsonl`) に存在すること。
- `elements` のキーがプレースホルダ定義と一致すること。
- `meta.content_hash` が `content_approved` のハッシュと一致すること（任意検証）。

## 変更履歴メモ
- 2025-10-11: `ai_patch` と `warnings` フィールドを追加。
- 2025-10-11: `fallback.history` をリスト形式へ変更。
（最新の詳細は git ログを参照）
