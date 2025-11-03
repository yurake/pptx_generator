# レンダリングスキーマ

工程4（レンダリング）で生成される JSON 仕様を定義する。

## ファイル
- `analysis.json`: レンダリング済みスライドの解析結果。文字数・空プレースホルダー・サイズ情報などを保持。
- `rendering_log.json`: レンダリング監査ログ。警告・エラー件数や実行時間を記録。
- `monitoring_report.json`: Analyzer/レンダリング/Polisher の統計値をまとめたメタ情報。監視・可観測性用途。
- `audit_log.json`: 最終成果物（PPTX/PDF）と中間ファイルのハッシュ、生成時刻、環境情報を集約した監査メタ。

## analysis.json
```jsonc
{
  "slides": [
    {
      "slide_id": "intro",
      "layout": "overview__one_col_v1",
      "warnings": ["textbox_overflow"],
      "placeholders": [
        {
          "name": "title",
          "text": "市場環境の変化",
          "characters": 12,
          "bbox": {"left": 0.5, "top": 0.8, "width": 11.0, "height": 1.2}
        }
      ]
    }
  ],
  "meta": {
    "template_id": "demo_v1",
    "generated_at": "2025-11-02T15:12:34+09:00",
    "issues_total": 3
  }
}
```

- `warnings`: Analyzer で検出された軽微な問題。`empty_placeholder`, `textbox_overflow`, `image_low_resolution` など。
- `placeholders[]`: プレースホルダーごとのテキスト長、バウンディングボックス、空要素の有無を保持する。

## rendering_log.json
```jsonc
{
  "meta": {
    "template_version": "demo_v1",
    "jobspec_hash": "sha256:...",
    "rendering_time_ms": 1420,
    "warnings_total": 1,
    "errors_total": 0
  },
  "warnings": [
    {
      "code": "textbox_overflow",
      "slide_id": "solution",
      "message": "本文がプレースホルダーを 8px 超過しました"
    }
  ]
}
```

### フィールド補足
- `meta.rendering_time_ms`: レンダリング処理に要した時間。`polisher_time_ms` 等の詳細統計を含める場合は `meta.timings` にネストする。
- `warnings`: Renderer が検出した警告一覧。`errors` セクションは致命的エラー発生時のみ使用。

## monitoring_report.json
```jsonc
{
  "rendering": {
    "warnings_total": 1,
    "errors_total": 0
  },
  "analyzer": {
    "issue_count": 2,
    "issue_counts_by_severity": {"warning": 2},
    "after_pipeline": "analysis.json"
  },
  "polisher": {
    "status": "disabled"
  }
}
```

- `rendering`: `rendering_log.json` の集計値。
- `analyzer`: `analysis.json` / `review_engine_analyzer.json` の集計値。
- `polisher.status`: `enabled` / `disabled` / `error` を想定。

## audit_log.json
```jsonc
{
  "pptx": {
    "path": "/path/to/proposal.pptx",
    "hash": "sha256:..."
  },
  "pdf": {
    "path": "/path/to/proposal.pdf",
    "hash": "sha256:...",
    "generated": true
  },
  "hashes": {
    "rendering_ready": "sha256:...",
    "rendering_log": "sha256:...",
    "analysis": "sha256:...",
    "monitoring_report": "sha256:..."
  },
  "rendering": {
    "warnings_total": 1,
    "errors_total": 0,
    "timings": {
      "total_ms": 1420,
      "pdf_ms": 620
    }
  },
  "environment": {
    "python": "3.12.8",
    "cli_version": "1.4.0",
    "libreoffice": "7.6",
    "polisher": null
  }
}
```

- `hashes`: 主要成果物・診断ファイルの SHA256。改ざん検知に利用する。
- `environment`: 再現性担保のためのバージョン情報。取得できない場合は null。

## バリデーション
- `analysis.json` の `slides` 配列と `rendering_ready.json` のスライド数が一致すること。
- `monitoring_report.json.rendering.warnings_total` が `rendering_log.json.meta.warnings_total` と一致すること。
- `audit_log.json.hashes` に記載されたファイルが存在し、ハッシュ検証が成功すること（CLI 側でチェック）。

## サンプル
- `samples/rendering_log.jsonc`
- `samples/analysis.jsonc`
- `samples/monitoring_report.jsonc`
- `samples/audit_log.jsonc`
