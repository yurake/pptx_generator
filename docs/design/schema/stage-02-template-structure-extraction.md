# ステージ2: テンプレ構造抽出スキーマ

工程2で生成する `layouts.jsonl`、`diagnostics.json`、`diff_report.json` の構造を定義する。

## layouts.jsonl
- JSON Lines 形式。1行につき1レイアウト。

```jsonc
{
  "template_id": "acme_v1",
  "layout_id": "overview__one_col_v1",
  "layout_name": "Overview - 1 Column",
  "placeholders": [
    {
      "name": "PH__Title__1",
      "type": "title",
      "bbox": {"x": 137160, "y": 68580, "width": 7010400, "height": 685800},
      "shape_type": "LayoutPlaceholder",
      "style_hint": {"font": "Noto Sans JP", "alignment": "center"}
    },
    {
      "name": "PH__Body__Main",
      "type": "body",
      "bbox": {"x": 137160, "y": 822960, "width": 7010400, "height": 4114800},
      "shape_type": "LayoutPlaceholder",
      "style_hint": {"font": "Noto Sans JP", "line_spacing": 1.3}
    },
    {
      "name": "PH__Logo__1",
      "type": "object",
      "bbox": {"x": 9310000, "y": 1600000, "width": 800000, "height": 800000},
      "shape_type": "LayoutPlaceholder"
    }
  ],
  "usage_tags": ["overview", "content", "visual"],
  "text_hint": {"max_chars": 400, "max_lines": 10},
  "media_hint": {"allow_table": true, "allow_chart": false, "allow_image": true},
  "placeholder_summary": {
    "counts": {"body": 1, "object": 1, "title": 1},
    "area_ratio": {"title": 0.52, "body": 0.35, "object": 0.13},
    "details": [
      {"name": "PH__Title__1", "type": "title", "area_ratio": 0.52},
      {"name": "PH__Body__Main", "type": "body", "area_ratio": 0.35},
      {"name": "PH__Logo__1", "type": "object", "area_ratio": 0.13}
    ],
    "attributes": {
      "total": 3,
      "has_title": true,
      "has_body": true,
      "has_table": false,
      "has_chart": false,
      "has_visual": true
    }
  },
  "heuristic": {
    "tags": ["content", "visual"],
    "reasons": ["placeholder:type=body", "placeholder:type=object(visual)"],
    "has_title_placeholder": true,
    "has_body_placeholder": true,
    "title_from_name": true
  },
  "static_rules": [],
  "meta": {
    "heuristic_reason": "placeholder:type=body; placeholder:type=object(visual); template_ai:fallback"
  },
  "version": "1.1.0"
}
```

### フィールド補足
- `bbox`: EMU 単位で位置・サイズを表す。
- `style_hint`: レンダリング・AI 補完のヒントであり、必須ではない。
- `usage_tags`: 工程5のスコアリングに利用する用途タグ。
- `text_hint.max_chars`: 面積から算出した推奨文字数。
- `placeholder_summary`: Stage3 での容量推定・意図タグ推定に利用する統計情報。詳細は `docs/design/stages/stage1-stage3-metadata-interface.md` を参照。

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
- Stage1 → Stage3 連携フィールド（`placeholder_summary.area_ratio` や Blueprint slot 情報など）をスキーマへ反映し、`docs/design/stages/stage1-stage3-metadata-interface.md` に沿って検証を追加する。
