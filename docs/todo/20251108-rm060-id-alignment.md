---
目的: Stage3 Drafter が JobSpec と BriefCard の ID を自動整合させ、不一致カードを検知前に補正する
関連ブランチ: fix/rm060-stage3-id-enforce
関連Issue: #277
roadmap_item: RM-060 Stage3 ID 整合性強制
---

- [x] ブランチ作成と初期コミット
  - メモ: fix/rm060-stage3-id-enforce ブランチを継続利用。前タスクで ID 検出の実装とテストを完了済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ:
    - 対象: DraftStructuring 直前に AI ベースの ID 整合ステップを挿入し、`prepare_card.json.cards[*].card_id` と `JobSpec.slides[*].id` の最適マッピングを生成する。
    - 前提: `content_ai` のクライアント／ポリシー仕組みを流用し、カード属性（章・intent・本文要約等）と JobSpec スライド情報（title/layout/stage情報）を AI へ渡す。
    - 戦略:
      - card_id ごとに AI が推奨 slide_id と信頼スコアを返すプロンプト設計。
      - 閾値以上は即適用、閾値未満は手動エラーへフォールバック（既存 missing_ids チェックを最終フェイルセーフとして残す）。
      - 補正結果と AI スコアをログ／メタに記録。
    - テスト: AI 呼び出しをモック化したユニットテスト、CLI 統合テストでズレた ID が補正されるシナリオを追加。全体は `uv run --extra dev pytest` で回帰確認。
- [ ] 設計・実装方針の確定
- [x] 設計・実装方針の確定
  - メモ: AI Slide Matcher のポリシー構成・信頼度閾値・エラーハンドリングを整理した。
- [ ] ドキュメント更新（要件・設計）
  - メモ: 新しい整合ロジックと優先順位、フォールバック条件を整理する。
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
- [ ] テスト・検証
  - メモ: CLI / pipeline レベルのテストで補正後に DraftStructuring が成功するケースを追加。
- [ ] ドキュメント更新
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
- [ ] PR 作成

## メモ
-
