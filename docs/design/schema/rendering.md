# レンダリング・監査スキーマ

工程6（PPTX レンダリング）および後続の PDF / 監査処理で利用する JSON 仕様を定義する。

## ファイル
- `rendering_log.json`: レンダリング実行時の警告と統計情報。
- `audit_log.json`: 監査用メタデータ。承認ログや生成物ハッシュを含む。

## rendering_log.json
```jsonc
{
  "slides": [
    {
      "page_no": 2,
      "layout_id": "overview__one_col_v1",
      "inserted_elements": {
        "title": true,
        "body": true,
        "table_data": true,
        "note": true
      },
      "warnings": [
        {"code": "table_overflow", "message": "列幅を自動調整しました"}
      ],
      "processing_ms": 120
    }
  ],
  "meta": {
    "template_version": "acme_v1",
    "rendering_time_ms": 1850,
    "warnings_total": 1
  }
}
```

## audit_log.json
```jsonc
{
  "job_id": "job-20251011-001",
  "template_version": "acme_v1",
  "rendering_ready_hash": "sha256:...",
  "output_pptx_hash": "sha256:...",
  "content_review_log_hash": "sha256:...",
  "draft_review_log_hash": "sha256:...",
  "pdf_export": {
    "enabled": true,
    "status": "success",
    "duration_ms": 2450
  },
  "polisher": {
    "enabled": true,
    "status": "success",
    "ruleset": "polish-default-v1"
  },
  "generated_at": "2025-10-11T12:30:00+09:00"
}
```

### フィールド補足
- `inserted_elements`: 各 PH で要素挿入が成功したかをブールで記録。
- `warnings.code`: `layout_mismatch`, `empty_placeholder`, `table_overflow`, `pdf_failed` など。
- `content_review_log_hash` / `draft_review_log_hash`: 承認ログとの連携に利用。
- `pdf_export.status`: `success` / `retry` / `failed` を想定。
- `polisher.status`: `.NET` Polisher の実行結果。`ruleset` は適用した設定名。

## サンプル
- `samples/rendering_log.jsonc`
- `samples/audit_log.jsonc`

## バリデーション
- ハッシュ値は `sha256:<hex>` 形式で統一。
- `warnings[].code` は定義済みコードのみ許容（別途定数で管理）。
- `pdf_export.enabled=false` の場合、`status` は省略可。

## 変更履歴
- 2025-10-11: 承認ログハッシュを追加し、HITL 追跡を強化。
- 2025-10-11: Polisher メタデータを拡張（ルールセット／ステータス）。
（詳細は `changelog.md` を参照）
