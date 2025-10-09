---
目的: ToDo/ロードマップ自動更新フローを構築し手動漏れを解消する
関連ブランチ: docs/auto-roadmap-completion
関連Issue: 未作成
roadmap_item: RM-002 エージェント運用ガイド整備
---

- [x] 作業用ブランチを作成し ToDo を更新
- [x] 自動更新に必要なメタデータ仕様を定義しテンプレートに反映
  - メモ: フロントマター項目とロードマップ対応情報を整理する
- [x] 自動完了スクリプトとテストを実装
  - メモ: `python scripts/auto_complete_todo.py --help` / `uv run --extra dev pytest tests/test_auto_complete_todo.py`
- [x] GitHub Actions ワークフローを追加し動作検証
  - メモ: `todo-auto-complete` 追加、`python3 scripts/auto_complete_todo.py --dry-run` で挙動確認
- [x] 運用ドキュメントとロードマップ/ToDo を更新し自動反映を確認
  - メモ: `AGENTS.md`, `docs/policies/task-management.md`, `docs/todo/README.md`, `scripts/AGENTS.md` を更新
- [ ] PR 作成
  - メモ: マージ後に自動化結果を再検証すること

## メモ
- Approval-First ポリシーに基づき Plan 承認済み（本スレッド）
- 既存の手動運用手順は `docs/policies/task-management.md` を参照
