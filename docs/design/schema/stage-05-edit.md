# stage 5 edit スキーマ

## API リクエスト（/edit）
- 必須: `pptx_path` (string) — 編集対象 PPTX へのパス
- 任意:
  - `edits_json` (string) — 差分 JSON のパス。指定時は LLM を呼び出さず適用のみ。
  - `edits` (array) — 差分を直接指定。`edits_json` より優先。指定時は LLM を呼び出さず適用のみ。
  - `transaction_id` (string) — 省略時はサーバが付与。

### `edits` 要素
```jsonc
{
  "shape_id": 256,
  "slide_index": 0,      // 任意（0-based）
  "name": "Title",       // 任意（名前一致で厳密化）
  "edit": true,          // 任意（false の場合スキップ）
  "contents": "新しい本文"
}
```

- `shape_id` と `contents` は必須。`slide_index`/`name` は照合を厳密化するための任意キー。
- `edit=false` の要素はスキップする。

## 内部記録: applied_edits.json（適用済み差分）
- 形式: `{ "edits": [<edits要素>...] }`
- 用途: 監査・再適用・検証向けの内部ログ（HTTP では公開しない）。
- 画像入力が有効な場合は `images/` と `edit_slide_images.json` を内部保存する（HTTP では公開しない）。

## 成果物
- 編集済み PPTX のみ（HTTP artifacts は `pptx_url` のみ）。JSON 成果物の URL は返さない。

## テスト観点
- `edits` 未指定時に LLM で差分生成→適用できること。
- `edits_json` / `edits` 指定時は LLM を呼び出さず適用されること。
- 適用失敗時（保存不可、LLM エラーなど）にジョブが failed となること。
- artifacts の `pptx_url` が HTTP で取得可能なこと。
