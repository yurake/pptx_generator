# ドラフト構成スキーマ

工程4（ドラフト構成設計）で利用する JSON 仕様を定義する。

## ファイル
- `draft_draft.json`: 章構成案と未承認スライドを保持。
- `draft_approved.json`: HITL 承認後、`layout_hint` が確定した状態。
- `draft_review_log.json`: 章・スライド単位の承認イベントログ。

## スキーマ構造
```jsonc
{
  "sections": [
    {
      "name": "市場概況",
      "order": 1,
      "status": "approved",
      "chapter_template_id": "bp-report-2025",
      "template_match_score": 0.86,
      "slides": [
        {
          "ref_id": "s01",
          "layout_hint": "overview",
          "locked": true,
          "status": "approved",
          "layout_candidates": [
            {"layout_id": "overview__one_col", "score": 0.92}
          ],
          "layout_score_detail": {
            "uses_tag": 0.45,
            "content_capacity": 0.25,
            "diversity": 0.12,
            "analyzer_support": 0.10
          },
          "analyzer_summary": {
            "severity_high": 0,
            "severity_medium": 1,
            "severity_low": 2,
            "layout_consistency": "ok"
          }
        }
      ]
    }
  ],
  "meta": {
    "target_length": 12,
    "structure_pattern": "report",
    "appendix_limit": 5,
    "template_id": "bp-report-2025",
    "template_match_score": 0.82,
    "return_reason_stats": {
      "STRUCTURE_GAP": 1,
      "ANALYZER_BLOCKER": 0
    }
  }
}
```

### フィールド補足
- `order`: 章 / スライドの表示順。整数で連番管理。
- `layout_hint`: 工程5で推奨されるレイアウト ID またはカテゴリ。必須。
- `layout_candidates`: Layout Hint Engine が算出した候補。`score` は 0〜1。
- `layout_score_detail`: 候補理由の内訳。`uses_tag`, `content_capacity`, `diversity`, `analyzer_support` の 4 指標を 0〜1 で表現する。
- `analyzer_summary`: Analyzer 由来の重大度別件数や `layout_consistency` 判定。
- `locked`: 承認済みフラグ。`true` の場合、工程3の再生成で上書き不可。
- `status`: `draft` / `approved` / `returned`。章単位とスライド単位の両方に付与。
- `chapter_template_id`: 適用された章テンプレートの ID。章・メタ双方に記録。
- `template_match_score`: 章テンプレ適合率。0〜1 で表現し、閾値未満は警告対象。
- `return_reason_stats`: 差戻しコード別件数のサマリ。`draft_meta.json` へ出力する。

### 承認ログ
```jsonc
{
  "target_type": "section",
  "target_id": "sec-01",
  "action": "approve",
  "actor": "approver@example.com",
  "timestamp": "2025-10-11T11:15:00+09:00",
  "notes": "付録送りは不要",
  "return_reason_code": "STRUCTURE_GAP",
  "return_reason_note": "章テンプレの必須セクションが不足しているため修正を依頼",
  "analyzer_summary": {"severity_high": 1, "severity_medium": 0, "severity_low": 0},
  "changes": {"slides": [{"ref_id": "s03", "status": "appendix"}]}
}
```

## サンプル
- `samples/draft_approved.jsonc`

## 章テンプレ辞書 (`config/chapter_templates/*.json`)
```jsonc
{
  "template_id": "bp-report-2025",
  "name": "BP 一般提案レポート",
  "structure_pattern": "report",
  "required_sections": [
    {"id": "market_overview", "title": "市場概況", "min_slides": 1, "max_slides": 2},
    {"id": "solution", "title": "提案ソリューション", "min_slides": 2, "max_slides": 4}
  ],
  "optional_sections": [
    {"id": "implementation", "title": "導入計画", "min_slides": 0, "max_slides": 3}
  ],
  "constraints": {
    "max_main_pages": 18,
    "appendix_policy": "overflow",
    "tags": ["enterprise", "bp"]
  }
}
```

### フィールド補足
- `required_sections[]`: 各章の最小・最大スライド数。`min_slides > 0` で必須。`max_slides` は `null` で無制限。
- `optional_sections[]`: 任意章。`min_slides` は 0 固定を推奨。
- `constraints.max_main_pages`: 本編上限。超過時は `draft_meta.template_mismatch` に `type="capacity"` で記録。
- `constraints.appendix_policy`: `overflow`（超過分を付録）、`allow`（本編超過許容し警告）、`block`（承認不可）。
- `constraints.tags[]`: テンプレ適用対象のカテゴリ。Spec 側 `story.tags` と一致しない場合は警告。

### バリデーション
- `template_id` は一意。
- `structure_pattern` は `draft_meta.structure_pattern` と一致する必要がある。
- `required_sections[].min_slides <= max_slides`。
- 登録された章 ID は Draft 出力の章 `name` / `id` とマッピングルールを保持する（ID/タイトル差異は `alias[]` で吸収予定）。

## 差戻し理由テンプレ (`return_reasons.json`)
```jsonc
[
  {
    "code": "STRUCTURE_GAP",
    "label": "章構成の不足",
    "description": "章テンプレで必須となっているセクションが不足しています。",
    "severity": "blocker",
    "default_actions": ["Add required section", "Escalate to story lead"],
    "related_analyzer_tags": ["missing_section"]
  },
  {
    "code": "ANALYZER_BLOCKER",
    "label": "Analyzer 指摘（重大）",
    "description": "重大度 High の Analyzer 指摘が解消されていません。",
    "severity": "blocker",
    "default_actions": ["Resolve analyzer issues"],
    "related_analyzer_tags": ["layout_consistency", "contrast_low"]
  }
]
```

### フィールド補足
- `severity`: `info` / `warn` / `blocker`。`blocker` は承認不可。
- `default_actions[]`: HITL 作業者が取るべきアクション候補を列挙。
- `related_analyzer_tags[]`: Analyzer の `issue.tag` と紐付け、警告優先度を制御。

### バリデーション
- `code` は重複不可。英数字＋アンダースコア。
- `severity=blocker` の場合、`default_actions` を最低 1 件含む。
- `related_analyzer_tags` のタグは Analyzer 仕様に存在するものを使用（存在しない場合は取り込み時に警告）。

## Analyzer サマリ (`analysis_summary.json`)
```jsonc
{
  "slides": [
    {
      "slide_uid": "s01",
      "severity_counts": {"high": 0, "medium": 1, "low": 2},
      "layout_consistency": "ok",
      "blocking_tags": [],
      "last_analyzed_at": "2025-10-22T09:12:00+09:00"
    },
    {
      "slide_uid": "s05",
      "severity_counts": {"high": 1, "medium": 0, "low": 0},
      "layout_consistency": "warn",
      "blocking_tags": ["layout_consistency"],
      "last_analyzed_at": "2025-10-22T09:12:00+09:00"
    }
  ]
}
```

### バリデーション
- `slide_uid` は Draft 内のスライドと一致する必要がある。
- `severity_counts` の値は 0 以上の整数。
- `blocking_tags[]` は重大度 High の要因のみ列挙。
- `last_analyzed_at` は ISO8601。Draft 取り込み時に 24 時間以上経過していれば警告。

## バリデーション
- 章 / スライドの `order` はユニーク。
- 本編スライド数が `meta.target_length` を超える場合は警告を出し、付録送りを促す。
- `layout_hint` がテンプレ構造で未定義の場合はエラー。
- `chapter_template_id` はテンプレ辞書に存在する必要がある。未一致時は `template_match_score` を 0 とする。
- 差戻しログ記録時は `return_reason_code` を必須とし、辞書に存在しないコードは拒否する。
- `layout_score_detail` の合計が 1.0 以内であること（浮動小数の丸め誤差は許容）。
- `analyzer_summary` は重大度別件数の合計と Analyzer 出力件数が一致する必要がある。

## 変更履歴メモ
- 2025-10-23: 章テンプレ辞書、差戻し理由テンプレ、Analyzer サマリ仕様を追加。
- 2025-10-23: 章テンプレ ID、スコア内訳、Analyzer サマリ、差戻し理由コードを追加。
- 2025-10-11: `layout_candidates` に `score` を追加。
- 2025-10-11: `status` を章レベルにも拡張。
（最新の詳細は git ログを参照）
