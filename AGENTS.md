# このドキュメントについて
- coding agent が作業前に確認すべき共通ルールを要約した Upfront ガイドです。
- 詳細手順や背景は `docs/policies/context-engineering.md`、各種ポリシー、Runbook、設計ドキュメントを参照してください。

# 1 基本原則
- 言語は日本語で統一する。
- コメントやメモで過去の変更に言及しない。

# 2 主要参照ドキュメント
- `docs/policies/context-engineering.md`: コンテキスト設計ポリシーと文書階層。
- `CONTRIBUTING.md`: 開発プロセス全体のガイドライン。
- `docs/policies/task-management.md`: Approval-First Development Policy と ToDo 運用。
- `docs/design/cli/cli-command-reference.md`: CLI コマンドとパイプライン詳細。
- `docs/requirements/requirements.md` / `docs/design/design.md`: 要件・設計の全体像。

# 3 環境セットアップ概要
- Python 3.12 系仮想環境で `uv sync` を実行し依存を整える（詳細: `CONTRIBUTING.md`）。
- LibreOffice（PDF 出力時）や .NET 8 SDK（仕上げツール利用時）など外部ツール要件は `docs/policies/config-and-templates.md` を確認する。
- `UV_CACHE_DIR=.uv-cache` など環境依存の回避策は Runbook／ポリシー側に記載。

# 4 CLI・テストの参照先
- Stage 別の CLI 実行手順やオプションは 2 章で挙げた CLI リファレンスを参照する。
- テスト戦略とコマンドは `tests/AGENTS.md` に集約。README では `uv run --extra dev pytest` を起点とした最小サマリのみ参照する。

# 5 タスク・ドキュメント運用
- ToDo 作成・更新、Plan 承認、ドキュメント反映は 2 章で挙げたタスク管理ポリシーと `docs/todo/README.md` に従う。
- ロードマップ管理やカテゴリ別ドキュメント更新手順は `docs/roadmap/roadmap.md`・`docs/README.md` を参照。

# 6 コミット / PR 方針
- Conventional Commits を採用し、小さな単位で履歴を残す。
- 作業ブランチは `feat|fix|chore|docs/rmxxx-<slug>` 形式。PR 作成時はテンプレート必須。
- 承認メッセージ ID・参照資料を PR と ToDo に記録する（具体的な手順はタスク管理ポリシーを参照）。

# 7 セキュリティ・外部ツール
- 機微情報は公開リポジトリに持ち込まない。必要に応じて `samples/` へ匿名化して配置する。
- `.env` は読み込まない。ツールバージョン差異の取り扱いは `docs/policies/config-and-templates.md` と関連 Runbook を参照。

# 8 Approval-First Development Policy
- すべての実装前に Plan を提示し、ユーザー承認を得る。
- scope / 影響ファイル / リスク / テスト / ロールバックを箇条書きにまとめ、承認後は ToDo の計画メモへ転記する。
- 詳細なチェックリストと例外対応はタスク管理ポリシーに記載されている。

# 9 サブディレクトリガイド
- `docs/` 系: `docs/README.md`（カテゴリ索引）、`docs/runbooks/`（運用手順）、`docs/policies/`（ルール）。
- コード系: `src/AGENTS.md`（実装ガイド）、`tests/AGENTS.md`（テスト設計）、`scripts/AGENTS.md`（スクリプト運用）。
- その他: `samples/AGENTS.md`、`config/AGENTS.md` など各ディレクトリ固有のガイドを参照。
