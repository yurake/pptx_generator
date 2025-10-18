---
目的: `pptx gen` の工程構成を再設計し、工程5/6の疎結合化と再実行性向上の方針を固める
関連ブランチ: feat/pipeline-decoupling
関連Issue: 未作成
roadmap_item: RM-023 コンテンツ承認オーサリング基盤
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/pipeline-decoupling を main から作成し、ToDo 追加コミット（docs(todo): track pipeline decoupling task）を作成済み。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: Approval-First Policy に基づき計画案を作成し、ユーザー承認メッセージ ID を記録する。
- [ ] 設計・実装方針の確定
  - メモ: 工程分割後の CLI 構成と `rendering_ready.json` 入力要件を整理する。
- [ ] ドキュメント更新（要件・設計）
  - メモ: 設計更新内容を docs/requirements・docs/design に反映する。
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: CLI コマンド分割、PipelineRunner 再構成、レンダラーの入力切り替えを実装。
- [ ] テスト・検証
  - メモ: CLI 統合テストを再構成し、工程別コマンドの再実行性を確認する。
- [ ] ドキュメント更新
  - メモ: 実施結果を docs/roadmap, README, runbooks へ反映し、影響範囲を整理する。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: 対応する Issue 作成後に更新する。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。todo-auto-complete が自動更新できない場合は理由を記載。

## メモ
-
