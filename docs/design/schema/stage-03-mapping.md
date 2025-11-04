# マッピングスキーマ

工程3（マッピング）で利用する JSON 仕様を定義する。

## ファイル
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
        "sources": ["intro"],
        "fallback": "none"
      }
    }
  ],
  "meta": {
    "template_version": "demo_v1",
    "content_hash": "sha256:...",
    "generated_at": "2025-11-02T12:05:00+09:00",
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

### フィールド補足
- `elements`: テンプレ側のアンカー名をキーにした構造。Renderer が直接利用する。
- `meta.sources`: 元コンテンツ（BriefCard）の `card_id` リスト。
- `meta.content_hash`: Brief 成果物から計算したハッシュ。差分検知に利用。
- `meta.fallback`: `none` / `shrink_text` / `split_slide` / `appendix` など。重大フォールバックは `fallback_report.json` と併用。

## mapping_log.json
```jsonc
{
  "slides": [
    {
      "ref_id": "intro",
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
        "issue_counts_by_type": {"font_min": 1, "contrast_low": 1},
        "issue_counts_by_severity": {"warning": 2},
        "issues": [
          {
            "issue_id": "font_min-intro-b1-1",
            "issue_type": "font_min",
            "severity": "warning",
            "message": "フォントサイズが下限を下回っています",
            "target": {"slide_id": "intro", "element_id": "b1", "element_type": "bullet"},
            "metrics": {"size_pt": 14.0, "min_size_pt": 18.0},
            "fix_type": "font_raise",
            "fix_payload": {"size_pt": 18.0}
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
    "analyzer_issue_counts_by_type": {"font_min": 1, "contrast_low": 1},
    "analyzer_issue_counts_by_severity": {"warning": 2}
  }
}
```

### フィールド補足
- `candidates`: レイアウト候補とスコア。`selected_layout` は最終採択値。
- `fallback.history`: `["shrink_text", "split_slide"]` のように適用順を記録。
- `ai_patch`: 適用された JSON Patch の ID と説明。差分は別途ログに記録。
- `warnings`: `layout_mismatch`, `table_overflow` など Renderer へ引き継ぐ警告。
- `analyzer`: 工程4で生成された Analyzer 指摘のスライド別サマリ。件数集計 (`issue_count`／`issue_counts_*`) と `analysis.json` の対象エントリを保持する。

## fallback_report.json
- 重大フォールバック（章削減、付録移動など）が発生したスライドのみを列挙する任意ファイル。
- 推奨フィールド: `ref_id`, `applied_strategy`, `reason`, `details`。

- `samples/generate_ready.jsonc`
- `samples/mapping_log.jsonc`

## バリデーション
- `generate_ready.json` の `layout_id` がテンプレ構造 (`layouts.jsonl`) に存在すること。
- `elements` のキーがプレースホルダ定義と一致すること。
- `meta.content_hash` が Brief 成果物のハッシュと一致すること（任意検証）。
