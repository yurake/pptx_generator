# ステージ1: テンプレ準備スキーマ

工程1ではテンプレート受け渡しの品質を確保するため、以下の成果物を想定する。

## ファイル
- `template_release.json`: テンプレートのメタ情報と検証結果を記録。
- `release_report.json`: 差分結果や警告一覧。
- `golden_runs/*.log`: ゴールデンサンプル実行ログ（任意）。

## template_release.json
```jsonc
{
  "template_id": "acme_v1",
  "brand": "ACME",
  "version": "1.0.0",
  "created_by": "designer@example.com",
  "created_at": "2025-10-12T09:30:00+09:00",
  "reviewed_by": "approver@example.com",
  "reviewed_at": "2025-10-12T10:15:00+09:00",
  "layouts": {
    "total": 32,
    "placeholders_avg": 6.5
  },
  "diagnostics": {
    "warnings": [],
    "errors": []
  },
  "hash": "sha256:ab12...ff"
}
```

## release_report.json
```jsonc
{
  "baseline": "acme_v0",
  "changes": {
    "layouts_added": ["overview__kpi_v2"],
    "layouts_removed": [],
    "placeholder_renamed": [
      {"from": "PH__Body__Main", "to": "PH__Body__Main_v2"}
    ]
  },
  "issues": [
    {"code": "duplicate_placeholder", "layout": "overview__kpi_v2", "name": "PH__Body__Main"}
  ]
}
```

## バリデーション
- `template_id`, `brand`, `version` は必須。
- `hash` はテンプレートファイルの SHA256。
- 差分で致命的な問題（重複 PH など）が検出された場合は `diagnostics.errors` に格納し、受け渡しを停止。

## サンプル
- `samples/template_release.jsonc`（準備予定）

## 今後のタスク
- 差分レポートのスキーマ確定とサンプル追加。
- ゴールデンサンプルログ形式の標準化。
- CLI (`template_release create`) の出力仕様策定。
