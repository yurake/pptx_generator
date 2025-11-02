# 工程4 マッピング スキーマ

工程4（ドラフト構成 + レイアウトマッピング）で利用する JSON 仕様を定義する。ドラフト関連の詳細は [stage-04-draft-structuring.md](stage-04-draft-structuring.md) を参照し、本ドキュメントではマッピング成果物（`generate_ready.json` など）を中心に記載する。

## ファイル
- `draft_draft.json` / `draft_approved.json` / `draft_meta.json`: ドラフト構成の成果物。HITL で編集され、4.2 のマッピング処理が入力として利用する（詳細は draft schema を参照）。
- `generate_ready.json`: レンダリングに必要なレイアウト決定済みデータ。
- `mapping_log.json`: 候補スコア、フォールバック、AI 補完履歴のログ。
- `fallback_report.json`: 収容不能など重大フォールバックの詳細（任意）。

## generate_ready.json
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
    "generated_at": "2025-10-11T12:05:00+09:00",
    "job_meta": {
      "schema_version": "1.1",
      "title": "次期プロジェクト提案",
      "client": "ABC 株式会社",
      "author": "営業部",
      "created_at": "2025-10-04",
      "theme": "corporate",
      "locale": "ja-JP"
    },
    "job_auth": {
      "created_by": "codex",
      "department": "solution"
    }
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
      "warnings": [],
      "analyzer": {
        "issue_count": 2,
        "issue_counts_by_type": {
          "font_min": 1,
          "contrast_low": 1
        },
        "issue_counts_by_severity": {
          "warning": 2
        },
        "issues": [
          {
            "issue_id": "font_min-s01-b1-1",
            "issue_type": "font_min",
            "severity": "warning",
            "message": "フォントサイズが下限を下回っています",
            "target": {
              "slide_id": "s01",
              "element_id": "b1",
              "element_type": "bullet"
            },
            "metrics": {
              "size_pt": 14.0,
              "min_size_pt": 18.0
            },
            "fix_type": "font_raise",
            "fix_payload": {
              "size_pt": 18.0
            }
          }
        ]
      }
    }
  ],
  "meta": {
    "mapping_time_ms": 845,
    "fallback_count": 0,
    "ai_patch_count": 1,
    "analyzer_issue_count": 2,
    "analyzer_issue_counts_by_type": {
      "font_min": 1,
      "contrast_low": 1
    },
    "analyzer_issue_counts_by_severity": {
      "warning": 2
    }
  }
}
```

### フィールド補足
- `elements` はテンプレ PH 名をキーにした構造。Renderer が直接利用する。
- `meta.sources`: 元コンテンツ (`content_approved`) の `slide_id` リスト。
- `fallback.history`: `["shrink_text", "split_slide"]` のように適用順を記録。
- `ai_patch`: 適用された JSON Patch の ID と説明。差分は別途ログに記録。
- `warnings`: `layout_mismatch`, `table_overflow` など Renderer へ引き継ぐ警告。
- `analyzer`: 工程5で生成された Analyzer 指摘のスライド別サマリ。件数集計 (`issue_count`／`issue_counts_*`) と `analysis.json` の対象エントリを保持する。
- `meta.job_meta` / `meta.job_auth`: 元 `JobSpec` のメタ情報を保持し、工程5での `JobSpec` 再構築に利用する。

## サンプル
- `samples/generate_ready.jsonc`
- `samples/mapping_log.jsonc`

## バリデーション
- `layout_id` がテンプレ構造 (`layouts.jsonl`) に存在すること。
- `elements` のキーがプレースホルダ定義と一致すること。
- `meta.content_hash` が `content_approved` のハッシュと一致すること（任意検証）。

## 変更履歴メモ
- 2025-10-21: `analyzer` セクションとメタの Analyzer 件数サマリを追加。
- 2025-10-18: `meta.job_meta` / `meta.job_auth` を追加。
- 2025-10-11: `ai_patch` と `warnings` フィールドを追加。
- 2025-10-11: `fallback.history` をリスト形式へ変更。
（最新の詳細は git ログを参照）
