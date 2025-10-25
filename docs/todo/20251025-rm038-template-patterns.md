---
目的: templates/templates.pptx にブランド準拠の新規レイアウトを追加し、RM-038 の期待成果に沿ったパターン拡充を行う
関連ブランチ: feat/rm038-template-patterns
関連Issue: #237
roadmap_item: RM-038 テンプレートパターン拡充
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/rm038-template-patterns を main から作成。初期コミット `docs(todo): add rm038 template pattern todo` を作成済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 2025-10-25 ユーザー承認（チャット返信「ok」）済み。Plan 内容を PR 用メモにも転記予定。
- [x] 設計・実装方針の確定
  - メモ: Timeline Detail / Comparison Two Axis / Fact Sheet を追加し、アンカー名を `Timeline Track` などへ統一する方針を決定。
- [x] ドキュメント更新（要件・設計）
  - メモ: 今回は要件・設計ドキュメントに追加変更が不要であることを確認済み。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: templates/templates.pptx に 3 レイアウト追加、sample_spec.json / renderer テスト・ポリシードキュメントを更新済み。
- [x] テスト・検証
  - メモ: `uv run pptx layout-validate --template samples/templates/templates.pptx` と `uv run --extra dev pytest` を完了。CLI 手動確認は必要に応じて実施予定。
- [x] ドキュメント更新
  - メモ: docs/policies/config-and-templates.md / samples/AGENTS.md を更新。その他カテゴリは今回変更不要であることを確認。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（今回変更なし）
  - [x] docs/design 配下（今回変更なし）
  - [x] docs/runbook 配下（今回変更なし）
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: Issue 作成後に番号を反映する。
- [ ] PR 作成
  - メモ: todo-auto-complete の動作を確認し、PR 番号を記録する。

## メモ
- 計画承認取得後に作業開始。
