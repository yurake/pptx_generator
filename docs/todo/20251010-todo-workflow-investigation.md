---
目的: todo-auto-complete ワークフローが main 上の ToDo に未完チェックを残す原因を調査し、対策案をまとめる
関連ブランチ: work
関連Issue: #139
roadmap_item: RM-002 エージェント運用ガイド整備
---

- [x] 調査 Plan を策定し承認を得る
- [x] docs/todo/ 配下の現状と自動化フローの仕様を確認する
  - メモ: ToDo のチェックボックス運用ルール、アーカイブ手順、ワークフロー記述を洗い出す
- [x] todo-auto-complete ワークフローと関連スクリプトの挙動を分析し、想定外のケースを特定する
  - メモ: `.github/workflows/todo-auto-complete.yml` と `scripts/auto_complete_todo.py`、関連テストを確認
- [x] 原因の仮説と再発防止策をまとめ、必要な修正・改善案を提案する
  - メモ: 追加で必要なドキュメント更新箇所があれば列挙
- [x] 調査結果をノートへ記録し、ToDo のメモを更新する
- [x] PR テンプレートに入力例と ToDo 記載チェックを追加する
- [x] `todo-auto-complete` の空検出時にワークフローを失敗させる
- [x] `todo-auto-complete` 後に ToDo の残存チェックを行う lint ステップを追加し、完了/完了間近が main に残らないことを自動検証する
- [ ] PR 作成
  - メモ: PR を作成したら番号と URL を記入する

## メモ
- 承認メッセージ: 2025-10-10 ユーザー指示「実施して」
- 調査ノート: [docs/notes/20251010-todo-workflow-investigation.md](../notes/20251010-todo-workflow-investigation.md)
  - ユーザー確認結果: 再発防止策はテンプレート強化とワークフローのエラー化を優先。lint 導入は不要との判断（2025-10-10 時点）。
  - 追加要望: `todo-auto-complete` 完了後に完了/完了間近の ToDo 残存を lint で検知し、PR 未記載ケースもブロックできるかを検証する。
