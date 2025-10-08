# ToDo 同期スクリプトのテスト追加

- 日付: 2025-10-08
- 担当: Codex

## 実施内容
- `scripts/sync_todo_to_issues.py` の関連 Issue 追記ロジックで末尾改行が壊れる不具合を修正。
- `tests/test_todo_sync_scripts.py` を新規追加し、タスク解析・関連 Issue 追記・Issues からのブロック生成を検証する自動テストを整備。
- `requests` への依存をテスト時にスタブ化し、HTTP を発生させずに単体検証できるようにした。
- ToDo ファイルをディレクトリ単位で探索し、`template.md` と `README.md` を除外した上で各ファイル専用ラベル・親 Issue を生成するよう同期スクリプトを全面改修。
- GitHub Actions (`todo-sync`) を簡素化し、`docs/todo/` 配下全体を対象に双方向同期を実行する構成へ変更。開発ブランチ上での push もトリガーされるよう分岐条件を撤廃。
- ToDo ファイルごとの固有ラベルを廃止し、`todo-sync` ラベルと本文内 `<!-- todo-path: ... -->` マーカーで紐付ける方式へ変更。
- 1 ファイル = 1 Issue の運用に切り替え、Issue 本文にチェックボックスをそのまま展開して双方向同期するよう実装。
- 旧仕様で生成されたタスク／親カード Issue は自動検出・クローズし、`todo-sync` ラベルを除去するクリーンアップを追加。
- ワークフローの自動コミット手順に `git stash` → `git pull --rebase` → `git stash pop` を組み込み、並列実行時のワークツリー衝突を回避。
- 並行ジョブが同じブランチへ push しても失敗しないよう、コミットステップで `git pull --rebase` を挟んで最新状態へ追従してから push するよう調整。
- ラベル生成の整合性およびファイル探索の挙動を検証する追加テストを実装。

## メモ
- CI でも `uv run --extra dev pytest tests/test_todo_sync_scripts.py` を実行して同期スクリプトの健全性を継続的に確認できるようにする。
- スケジュールトリガーは削除したため、`push` と `workflow_dispatch`、および Issue イベントで十分にカバーできるか今後の運用で確認する。
