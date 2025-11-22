# ステージ1: テンプレ準備スキーマ

工程1ではテンプレート受け渡しの品質を確保するため、以下の成果物を想定する。

## ファイル
- `template_spec.json`: テンプレ抽出結果。`layout_mode` や Blueprint を含むテンプレ構造を表現し、`jobspec.json.meta.template_spec_path` から参照される。
- `template_release.json`: テンプレートのメタ情報と検証結果を記録。
- `release_report.json`: 差分結果や警告一覧。
- `golden_runs/*.log`: ゴールデンサンプル実行ログ（任意）。

## Blueprint スキーマ
- 静的テンプレートを扱う場合は `template_spec.json.blueprint` にスライド順と slot 情報を保持する。
- `layout_mode` は `dynamic` / `static` を取り、`static` の場合は Blueprint を必須とする。
- `jobspec.json.meta.template_spec_path` には `template_spec.json` への相対パスを記録し、工程2/3 から Blueprint を参照できるようにする。

```jsonc
{
  "template_path": "templates/acme/static_v1/template.pptx",
  "layout_mode": "static",
  "blueprint": {
    "slides": [
      {
        "slide_id": "cover",
        "layout": "Title",
        "intent_tags": ["opening"],
        "slots": [
          {
            "slot_id": "cover.title",
            "anchor": "Title",
            "content_type": "text",
            "required": true
          },
          {
            "slot_id": "cover.subtitle",
            "anchor": "Sub Title",
            "content_type": "text",
            "required": false
          }
        ]
      }
    ]
  }
}
```

- `slides[*].layout` は抽出済みレイアウト名と一致させる。
- `slots[*].anchor` はテンプレ内の shape 名に一致させ、`required=true` の slot は工程2/3 で必須充足を検査する。
- `content_type` は `text` / `image` / `table` / `chart` / `shape` / `other` を想定し、工程2 のカード生成と工程3 のマッピングに利用する。

### 自動描画プレースホルダーの扱い
- PowerPoint が自動描画するプレースホルダー（例: `SLIDE_NUMBER`、`DATE`／`DATETIME`、`FOOTER`、`HEADER`）は `jobspec.json` にそのまま残るが、`auto_draw=true` が付与される。  
- Blueprint には自動描画プレースホルダーの slot を生成しないため、工程2/3 のカード整形でコンテンツ差し込み対象とはならない。  
- 実装側（レンダラー等）は `auto_draw` を判定してテンプレート既定の描画枠を維持する。  
- 上記以外のプレースホルダーは従来通り jobspec に残り、工程2 以降でコンテンツ差し込み対象となる。

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
