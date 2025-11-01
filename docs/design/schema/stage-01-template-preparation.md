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
  "template_path": "templates/libraries/acme/v1/template.pptx",
  "hash": "sha256:ab12...ff",
  "generated_at": "2025-10-12T10:45:00+09:00",
  "generated_by": "designer@example.com",
  "reviewed_by": "approver@example.com",
  "layouts": {
    "total": 32,
    "placeholders_avg": 6.5,
    "details": [
      {
        "name": "title_cover",
        "anchor_count": 4,
        "placeholder_count": 3,
        "anchor_names": [
          "PH__Title",
          "PH__Subtitle",
          "PH__Note",
          "Logo"
        ],
        "placeholder_names": [
          "PH__Title",
          "PH__Subtitle",
          "PH__Note"
        ],
        "duplicate_anchor_names": [],
        "issues": []
      },
      {
        "name": "overview__kpi_v2",
        "anchor_count": 6,
        "placeholder_count": 4,
        "anchor_names": [
          "PH__Title",
          "PH__Body__Main",
          "PH__Body__Sub",
          "PH__Note__01",
          "PH__Note__02",
          "body"
        ],
        "placeholder_names": [
          "PH__Title",
          "PH__Body__Main",
          "PH__Body__Sub",
          "PH__Note__01"
        ],
        "duplicate_anchor_names": [
          "PH__Body__Main"
        ],
        "issues": [
          "missing_fields: width",
          "conflict: SlideBullet拡張仕様で使用される可能性のあるアンカー名: body"
        ]
      }
    ]
  },
  "diagnostics": {
    "warnings": [
      "layout overview__kpi_v2: duplicate anchor PH__Body__Main",
      "shape body in overview__kpi_v2: SlideBullet拡張仕様で使用される可能性のあるアンカー名: body"
    ],
    "errors": []
  },
  "golden_runs": [
    {
      "spec_path": "samples/json/sample_jobspec.json",
      "status": "passed",
      "output_dir": ".pptx/release/golden_runs/sample_jobspec",
      "pptx_path": ".pptx/release/golden_runs/sample_jobspec/sample_jobspec.pptx",
      "analysis_path": ".pptx/release/golden_runs/sample_jobspec/analysis.json",
      "pdf_path": null,
      "warnings": [],
      "errors": []
    }
  ]
}
```

## release_report.json
```jsonc
{
  "template_id": "acme_v1",
  "baseline_id": "acme_v0",
  "generated_at": "2025-10-12T10:45:01+09:00",
  "hashes": {
    "current": "sha256:ab12...ff",
    "baseline": "sha256:9f32...cc"
  },
  "changes": {
    "layouts_added": [
      "overview__kpi_v2"
    ],
    "layouts_removed": [],
    "layout_diffs": [
      {
        "name": "overview__kpi_v2",
        "anchors_added": [
          "PH__Note__02"
        ],
        "anchors_removed": [],
        "placeholders_added": [
          "PH__Note__02"
        ],
        "placeholders_removed": [],
        "duplicate_anchor_names": [
          "PH__Body__Main"
        ]
      }
    ]
  },
  "diagnostics": {
    "warnings": [
      "layout overview__kpi_v2: duplicate anchor PH__Body__Main"
    ],
    "errors": []
  }
}
```

## バリデーション
- `template_id`, `brand`, `version`, `template_path`, `hash`, `generated_at` は必須。`generated_by` と `reviewed_by` は任意だが、利用時には雛形に沿って設定する。
- `hash` はテンプレートファイルの SHA256。フォーマットは `sha256:<digest>` とする。
- `layouts.details[*].duplicate_anchor_names` は重複名がある場合に列挙する。`issues` には `missing_fields:` や `conflict:` など検出状況をメッセージ形式で記録する。
- 差分で致命的な問題（重複 PH や抽出エラーなど）が検出された場合は `diagnostics.errors` に格納し、受け渡しを停止。CI 連携時は `errors` が空かどうかで合否を判定する。
- `golden_runs[*].status` は `passed` または `failed`。失敗時は `diagnostics.errors` にもメッセージを記録し、`errors` フィールドへ理由を残す。

## サンプル
- `samples/template_release.jsonc`
- `samples/template_release_report.jsonc`
- `samples/template_golden_runs.jsonc`

## 今後のタスク
- 差分レポートのスキーマ確定とサンプル追加（`docs/design/schema/samples/template_release_report.jsonc`）。
- ゴールデンサンプルログ形式の標準化。
- CLI (`tpl-release`) の出力仕様策定。
