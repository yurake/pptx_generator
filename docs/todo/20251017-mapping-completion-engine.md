---
目的: RM-025 マッピング補完エンジンの設計および実装によりマッピング品質を底上げする
関連ブランチ: feat/mapping-completion-engine
関連Issue: #175
roadmap_item: RM-025 マッピング補完エンジン
---

- [ ] ブランチ作成と初期コミット
  - メモ: 担当: Codex / 完了条件: feat/mapping-completion-engine ブランチで初期コミット（ToDo 追加など最小差分）を作成し push する
- [ ] 計画策定（スコープ・前提・担当の整理）
  - メモ: 担当: Codex / 完了条件: Approval-First ポリシーに沿った Plan を提示し、ユーザー承認メッセージ ID を記録する
- [ ] 設計・実装方針の確定
  - メモ: 担当: Codex / 完了条件: マッピング補完エンジンの構造や API を文書化し、承認済み Plan と整合することを確認する
- [ ] ドキュメント更新（要件・設計）
  - メモ: 担当: Codex / 完了条件: 影響する要件・設計ドキュメントを更新し、レビュー観点の記録を残す
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: 担当: Codex / 完了条件: スコアリング・フォールバック・AI 補完ロジックを含むマッピング補完エンジンを実装し、既存フローと統合する
- [ ] テスト・検証
  - メモ: 担当: Codex / 完了条件: 追加した単体・統合テストを `uv run --extra dev pytest` で実行し結果を記録する
- [ ] ドキュメント更新
  - メモ: 担当: Codex / 完了条件: 実装結果に基づく各種ドキュメントを更新し、差分なしの場合も判断理由をメモする
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: 担当: Codex / 完了条件: ToDo フロントマターの `関連Issue` を最新の Issue 番号へ更新し、追記メモを残す
- [ ] PR 作成
  - メモ: 担当: Codex / 完了条件: PR 作成後に todo-auto-complete ワークフローの結果を確認し、PR 番号と URL を記録する

## メモ
- 承認メッセージ ID、テスト結果、検討メモを随時追記する
