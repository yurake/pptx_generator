# レンダリング・監査スキーマ

工程5（PPTX レンダリング）および後続の PDF / 監査処理で利用する JSON 仕様を定義する。

## ファイル
- `analysis_pre_polisher.json`: Renderer 出力直後の Analyzer 結果（比較用ベースライン）。
- `rendering_log.json`: レンダリング実行時の警告と統計情報。
- `audit_log.json`: 監査用メタデータ。承認ログや生成物ハッシュを含む。
- `monitoring_report.json`: レンダリング監査・Analyzer before/after の突合レポート。

## rendering_log.json
```jsonc
{
  "meta": {
    "generated_at": "2025-10-19T03:15:00Z",
    "template_version": "acme_v1",
    "rendering_time_ms": 1850,
    "warnings_total": 2,
    "empty_placeholders": 1
  },
  "slides": [
    {
      "page_no": 1,
      "layout_id": "title__main_v1",
      "detected": {
        "title": true,
        "subtitle": false,
        "body": false,
        "notes": false
      },
      "warnings": [
        {"code": "missing_subtitle", "message": "subtitle プレースホルダーが空です"},
        {"code": "empty_placeholder", "message": "プレースホルダー 'Content Placeholder 2' が空です"}
      ]
    }
  ]
}
```

## audit_log.json
```jsonc
{
  "generated_at": "2025-10-19T03:15:02Z",
  "spec_meta": {
    "title": "Acme Quarterly Deck",
    "schema_version": "proposal-v3",
    "locale": "ja-JP"
  },
  "slides": 18,
  "artifacts": {
    "pptx": ".pptx/gen/proposal.pptx",
    "analysis": ".pptx/gen/analysis.json",
    "analysis_pre_polisher": ".pptx/gen/analysis_pre_polisher.json",
    "rendering_log": ".pptx/gen/rendering_log.json",
    "monitoring_report": ".pptx/gen/monitoring_report.json",
    "pdf": ".pptx/gen/proposal.pdf"
  },
  "hashes": {
    "generate_ready": "sha256:41b4...f0",
    "pptx": "sha256:92ff...0a",
    "analysis": "sha256:ab12...9f",
    "analysis_pre_polisher": "sha256:f41c...aa",
    "monitoring_report": "sha256:0a1b...ef",
    "pdf": "sha256:ff10...cc"
  },
  "rendering": {
    "warnings_total": 2,
    "empty_placeholders": 1
  },
  "pdf_export": {
    "enabled": true,
    "status": "success",
    "attempts": 1,
    "elapsed_ms": 2450,
    "converter": "libreoffice"
  },
  "polisher": {
    "enabled": true,
    "status": "success",
    "elapsed_ms": 420,
    "rules_path": "config/polisher-rules.json",
    "summary": {
      "font_adjustments": 5,
      "color_adjustments": 2
    }
  },
  "monitoring": {
    "alert_level": "warning",
    "headline": "2 slides require attention",
    "rendering_warnings": 2,
    "analyzer_issues": 4
  }
}
```

### フィールド補足
- `detected`: title/subtitle/body/notes の検出状況をブールで記録。
- `warnings.code`: `missing_title` / `missing_subtitle` / `missing_body` / `empty_placeholder` などの定義済みコード。
- `hashes`: 主要成果物の `sha256:<hex>` を格納する。
- `pdf_export.status`: `success` / `retry` / `failed` を想定し、`attempts`, `elapsed_ms`, `converter` を併記する。
- `polisher.status`: `.NET` Polisher の実行結果。`rules_path` と `summary` (JSON) を任意で格納。
- `monitoring`: CI 連携向けのアラートサマリ（`monitoring_report.json` を凝縮）。

## monitoring_report.json
`rendering_log.json` と Analyzer before/after の突合結果を保持する。構造の詳細は `samples/monitoring_report.jsonc` を参照。

## サンプル
- `samples/analysis_pre_polisher.jsonc`（※必要に応じて生成）
- `samples/rendering_log.jsonc`
- `samples/audit_log.jsonc`
- `samples/monitoring_report.jsonc`

## バリデーション
- ハッシュ値は `sha256:<hex>` 形式で統一。
- `warnings[].code` は定義済みコードのみ許容（別途定数で管理）。
- `pdf_export.enabled=false` の場合、`status` は省略可。

## 変更履歴メモ
- 2025-10-11: 承認ログハッシュを追加し、HITL 追跡を強化。
- 2025-10-11: Polisher メタデータを拡張（ルールセット／ステータス）。
- 2025-10-21: Monitoring レポートと Analyzer before/after を追加。
（最新の詳細は git ログを参照）
