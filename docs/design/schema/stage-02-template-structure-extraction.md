# ステージ2: テンプレ構造抽出スキーマ

工程2で生成する `layouts.jsonl`、`diagnostics.json`、`diff_report.json` の構造を定義する。

## layouts.jsonl
- JSON Lines 形式。1行につき1レイアウト。

```jsonc
{
  "template_id": "acme_v1",
  "layout_id": "overview__one_col_v1",
  "placeholders": [
    {
      "name": "PH__Title__1",
      "type": "title",
      "bbox": {"x": 137160, "y": 68580, "width": 7010400, "height": 685800},
      "style_hint": {"font": "Noto Sans JP", "alignment": "center"}
    },
    {
      "name": "PH__Body__Main",
      "type": "body",
      "bbox": {"x": 137160, "y": 822960, "width": 7010400, "height": 4114800},
      "style_hint": {"font": "Noto Sans JP", "line_spacing": 1.3}
    }
  ],
  "usage_tags": ["overview", "content"],
  "text_hint": {"max_chars": 400, "max_lines": 10},
  "media_hint": {"allow_table": true, "allow_chart": false},
  "version": "1.0.0"
}
```

### フィールド補足
- `bbox`: EMU 単位で位置・サイズを表す。
- `style_hint`: レンダリング・AI 補完のヒントであり、必須ではない。
- `usage_tags`: 工程5のスコアリングに利用する用途タグ。
- `text_hint.max_chars`: 面積から算出した推奨文字数。

## diagnostics.json
```jsonc
{
  "template_id": "acme_v1",
  "warnings": [
    {"code": "placeholder_unknown_type", "layout_id": "overview__kpi_v2", "name": "PH__Custom__1"}
  ],
  "errors": [
    {"code": "duplicate_placeholder", "layout_id": "overview__kpi_v2", "name": "PH__Body__Main"}
  ],
  "stats": {
    "layouts_total": 32,
    "placeholders_total": 210,
    "extraction_time_ms": 8450
  }
}
```

### レベル
- `warnings`: 後工程で回避可能な問題（未知の PH 種別など）。
- `errors`: 致命的な問題（重複 PH、抽出失敗）。存在する場合は工程を停止する。

## diff_report.json
```jsonc
{
  "baseline_template_id": "acme_v0",
  "target_template_id": "acme_v1",
  "layouts_added": ["overview__kpi_v2"],
  "layouts_removed": [],
  "placeholders_changed": [
    {"layout_id": "overview__one_col_v1", "name": "PH__Body__Main", "field": "bbox"}
  ],
  "issues": [
    {"code": "placeholder_missing", "layout_id": "overview__one_col_v1", "name": "PH__Note__1"}
  ]
}
```

## バリデーション
- `template_id`, `layout_id`, `placeholders[].name` は必須。
- `placeholders[].type` は既定の enum（`title`, `body`, `note`, `table`, `image`, `chart`, `subtitle`, `label`）を推奨。
- `diagnostics.errors` が空でない場合はテンプレ受け渡しを差し戻す。
- `src/pptx_generator/layout_validation/schema.py` に JSON Schema を実装し、`layout-validate` コマンド実行時に `jsonschema` で検証する。

## サンプル
- `samples/layouts.jsonl`（準備予定）
- `samples/diagnostics.jsonc`（準備予定）

## 今後のタスク
- `layouts.jsonl` スキーマを JSON Schema として定義し、CI で検証する。
- 差分レポート出力の標準化とサンプル追加。
- `usage_tags` 推定ロジックの指標化とテスト整備。
- JSON Lines サンプルを `docs/design/schema/samples/` に追加し、レポート生成例を整備する。
