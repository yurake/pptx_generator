---
目的: ロードマップおよび関連設計・要件ドキュメントのリネームと自動更新スクリプトの調整
関連ブランチ: docs/rename-roadmap-refs
関連Issue: #211
roadmap_item: RM-002 エージェント運用ガイド整備
---

- [x] ブランチ作成と初期コミット
  - メモ: main から docs/rename-roadmap-refs を作成し、ToDo 追加のみを含む初期コミットを実施。
- [x] 計画策定（スコープ・前提・担当の整理）
  - メモ: ユーザー承認済み（2025-10-17）。範囲はファイルリネーム/参照更新と Mermaid ステータス更新ロジック改修。
- [x] 設計・実装方針の確定
  - メモ: Mermaid ノードのステータス置換を `RMxxx` ID 単位で実施する方針を決定。
- [x] ドキュメント更新（要件・設計）
  - メモ: リネームと参照更新を全体へ反映。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `mark_mermaid_task_complete` を追加し、完了時に Mermaid 状態も更新。
- [x] テスト・検証
  - メモ: `python -m compileall scripts/auto_complete_todo.py` / `--dry-run` 実行で挙動確認。
- [x] ドキュメント更新
  - メモ: 各種ガイド・ノートの参照リンクを新ファイル名へ更新。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: #211 を紐付け済み。
- [ ] PR 作成
  - メモ: 

## メモ
- 
