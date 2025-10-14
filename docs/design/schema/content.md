# コンテンツ承認スキーマ

工程3（コンテンツ正規化）の入力・出力 JSON 仕様を定義する。

## ファイル
- `content_draft.json`: AI 生成の初稿。承認前のカードを保持。
- `content_approved.json`: HITL 承認後の確定版。ロック情報と適用済み Auto-fix を記録。
- `content_review_log.json`: 承認・差戻しイベントの監査ログ。

## スキーマ構造
```jsonc
{
  "slides": [
    {
      "id": "s01",
      "intent": "市場動向",
      "type_hint": "content",
      "elements": {
        "title": "市場環境の変化",
        "body": ["国内需要は前年比12%増", "海外市場は為替影響で横ばい"],
        "table_data": { "headers": ["指標", "前年比"], "rows": [["売上", "112%"]] },
        "note": "為替前提は110円/ドル"
      },
      "ai_review": {
        "grade": "B",
        "issues": [{"code": "text_too_long", "message": "本文が40文字を超過"}],
        "autofix_proposals": [
          {"patch_id": "p01", "description": "本文2文目を要約", "patch": {"op": "replace", "path": "/elements/body/1", "value": "海外市場は横ばい"}}
        ]
      },
      "status": "draft"
    }
  ],
  "meta": {
    "tone": "formal",
    "audience": "management",
    "summary": "提案書ドラフトのポイント"
  }
}
```

### フィールド補足
- `intent`: 工程5のレイアウト選定で利用する用途タグ。必須。
- `type_hint`: `content`, `title`, `kpi` などマッピング優先度に利用。
- `ai_review.grade`: `A` / `B` / `C` の3段階評価。`C` は承認不可。
- `ai_review.autofix_proposals[].patch`: JSON Patch 互換。適用時は `applied_autofix` に履歴を記録。
- `status`: `draft` / `approved` / `returned`。`content_approved.json` ではすべて `approved`。

### 承認ログ
```jsonc
{
  "slide_id": "s01",
  "action": "approve",
  "actor": "editor@example.com",
  "timestamp": "2025-10-11T09:32:00+09:00",
  "notes": "Auto-fix p01 適用",
  "applied_autofix": ["p01"]
}
```

## サンプル
- `samples/content_approved.jsonc`

## バリデーション
- `id`, `intent`, `elements.title` は必須。
- `elements.body` は文字列配列、最大 6 行、各行 40 文字以内（バリデータで検証）。
- `ai_review` は `content_draft.json` のみ必須。`content_approved.json` では省略可。

## 変更履歴
- 2025-10-11: `ai_review.autofix_proposals.patch` を JSON Patch 形式に統一。
- 2025-10-11: `status` フィールドを追加し、承認状態を明示化。
（詳細は `changelog.md` を参照）
