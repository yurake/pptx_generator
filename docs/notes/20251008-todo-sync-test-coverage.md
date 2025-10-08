# ToDo 同期スクリプトのテスト追加

- 日付: 2025-10-08
- 担当: Codex

## 実施内容
- `scripts/sync_todo_to_issues.py` の関連 Issue 追記ロジックで末尾改行が壊れる不具合を修正。
- `tests/test_todo_sync_scripts.py` を新規追加し、タスク解析・関連 Issue 追記・Issues からのブロック生成を検証する自動テストを整備。
- `requests` への依存をテスト時にスタブ化し、HTTP を発生させずに単体検証できるようにした。

## メモ
- CI でも `uv run --extra dev pytest tests/test_todo_sync_scripts.py` を実行して同期スクリプトの健全性を継続的に確認できるようにする。
