# tests ディレクトリ向け作業指針

## テスト構成
- 単体テスト: `tests/test_*.py` に配置。レンダラー・アナライザー・モデルなどコンポーネント単位の挙動を検証する。
- 統合テスト: `tests/test_cli_integration.py` が CLI から PPTX/PDF を生成するフローをカバー。サンプル JSON は `samples/` を利用。
- 補助スクリプト: `tests/test_todo_sync_scripts.py` で `scripts/` 配下の GitHub 同期ロジックを検証。

## 実行コマンド
- すべてのテスト: `uv run --extra dev pytest`
- 単一テストモジュール: `uv run --extra dev pytest tests/test_renderer.py`
- 統合テストのみ: `uv run --extra dev pytest tests/test_cli_integration.py -k "not pdf" --maxfail=1`
- PDF 変換を含むテストは LibreOffice が必要なため、実行前に `soffice --headless --version` で環境確認する。

## 追加・更新ポリシー
- 新機能やバグフィックスでは必ず失敗パターンを先に再現させるテストを追加し、緑化を確認する。
- 大きな生成物（PPTX/PDF）の内容確認は、ハッシュ比較や `analysis.json` のメタ情報で検証し、バイナリをリポジトリに含めない。
- テストデータを追加する場合は `samples/` に配置し、目的や前提条件をファイル冒頭にコメントとして記載する。

## レビュー時確認ポイント
- テスト名・アサーションが意図を明確に伝えているか。
- `pytest` マーカーやフィクスチャの再利用可否を確認し、重複があれば共通化を検討する。
- CI 上で実行可能なコマンドのみ使用しているか（外部サービスへの依存はモック化する）。
