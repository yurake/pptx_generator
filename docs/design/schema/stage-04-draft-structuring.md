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
      "slides": [
        {
          "ref_id": "s01",
          "layout_hint": "overview",
          "locked": true,
          "status": "approved",
          "layout_candidates": [
            {"layout_id": "overview__one_col", "score": 0.92}
          ]
        }
      ]
    }
  ],
  "meta": {
    "target_length": 12,
    "structure_pattern": "report",
    "appendix_limit": 5
  }
}
```

### フィールド補足
- `order`: 章 / スライドの表示順。整数で連番管理。
- `layout_hint`: 工程5で優先的に使用するレイアウト ID またはカテゴリ。必須。
- `layout_candidates`: Layout Hint Engine が算出した候補。`score` は 0〜1。
- `locked`: 承認済みフラグ。`true` の場合、工程3の再生成で上書き不可。
- `status`: `draft` / `approved` / `returned`。章単位とスライド単位の両方に付与。

### 承認ログ
```jsonc
{
  "target_type": "section",
  "target_id": "sec-01",
  "action": "approve",
  "actor": "approver@example.com",
  "timestamp": "2025-10-11T11:15:00+09:00",
  "notes": "付録送りは不要",
  "changes": {"slides": [{"ref_id": "s03", "status": "appendix"}]}
}
```

## サンプル
- `samples/draft_approved.jsonc`

## バリデーション
- 章 / スライドの `order` はユニーク。
- 本編スライド数が `meta.target_length` を超える場合は警告を出し、付録送りを促す。
- `layout_hint` がテンプレ構造で未定義の場合はエラー。

## 変更履歴
- 2025-10-11: `layout_candidates` に `score` を追加。
- 2025-10-11: `status` を章レベルにも拡張。
（詳細は `changelog.md` を参照）
