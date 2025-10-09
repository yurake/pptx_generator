# scripts ディレクトリ向け作業指針

## 対象スクリプト
- `sync_todo_to_issues.py`: `docs/todo/` の Markdown と GitHub Issues を双方向で同期するユーティリティ。

## 実行前の準備
- 必要な環境変数:
  - `GITHUB_TOKEN`（`repo` 権限付き PAT）: GitHub API 呼び出しで使用。
  - `GITHUB_REPOSITORY`（`owner/repo` 形式）: 省略した場合は引数で指定する。
- 依存ライブラリ: `requests`（`uv sync` 後に自動導入）。単体実行時は `uv run python scripts/sync_todo_to_issues.py --help` で CLI オプションを確認。

## サポートされる主なオプション
- `--todo docs/todo/YYYYMMDD-*.md`: 同期対象の ToDo ファイルを指定（未指定時は全ファイル走査）。
- `--label name`: Issue 作成時に付与するラベル。
- `--dry-run`: GitHub API を呼ばず、ローカルで差分を出力して確認する。

## 実装・修正時の注意
- 正規表現は `TASK_RE` など既存のパターンを流用し、ToDo フォーマットの逸脱を防ぐ。
- API 呼び出し失敗時は例外メッセージに HTTP ステータスとレスポンス本文を含める（既存実装は `RuntimeError` を送出）。
- スクリプトを更新した際は `tests/test_todo_sync_scripts.py` にテストケースを追加し、API 呼び出し箇所はモック化する。

## レビュー時確認ポイント
- 実行手順と引数の説明が `README.md` や関連ドキュメントに反映されているか。
- 新しいオプションを追加した際はデフォルト挙動が変わらないこと、または変更点が周知されていることを確認する。
- GitHub API レート制限に配慮し、不要なリクエストが発生していないか（paging・キャッシュなど）。
