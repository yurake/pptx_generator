---
目的: templates/templates.pptx にブランド準拠の新規レイアウトを追加し、RM-038 の期待成果に沿ったパターン拡充を行う
関連ブランチ: feat/rm038-template-patterns
関連Issue: #237
roadmap_item: RM-038 テンプレートパターン拡充
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/rm038-template-patterns を main から作成。初期コミット `docs(todo): add rm038 template pattern todo` を作成済み。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: ユーザー承認待ち。Plan 提示時に参照メッセージ ID を記録する。
- [ ] 設計・実装方針の確定
  - メモ: 新規レイアウト種別と命名規約の調整ポイントを整理する。
- [ ] ドキュメント更新（要件・設計）
  - メモ: RM-038 に紐づく要件整理が必要になった場合は docs/notes を含め検討する。
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: templates/templates.pptx へのレイアウト追加と layout ヒント更新を想定。詳細は Plan 承認後に確定。
- [ ] テスト・検証
  - メモ: uv run --extra dev pytest と CLI レンダリング確認を予定。
- [ ] ドキュメント更新
  - メモ: 変更内容に応じて docs/policies/config-and-templates.md 等を更新する。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: Issue 作成後に番号を反映する。
- [ ] PR 作成
  - メモ: todo-auto-complete の動作を確認し、PR 番号を記録する。

## メモ
- 計画承認取得後に作業開始。
