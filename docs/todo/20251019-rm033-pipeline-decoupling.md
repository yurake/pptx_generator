---
目的: 工程3/4独立 CLI 化に向けた要件整理とプロトタイプ設計・実装・検証を行い、RM-033 の初動を完了させる
関連ブランチ: feat/rm033-pipeline-decoupling
関連Issue: #218
roadmap_item: RM-033 パイプライン工程3/4独立化準備
---

- [x] ブランチ作成と初期コミット
  - メモ: `feat/rm033-pipeline-decoupling` を main から作成し、初期コミット `docs(task-management): align todo flow with approval-first policy` を作成。承認メッセージ（ユーザー 2025-10-19 指示）をコミット本文へ記録済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: Plan を提示済み。ユーザー質問・指示を踏まえて承認済みとして進行。
- [x] 設計・実装方針の確定
  - メモ: `docs/design/20251019-stage3-4-cli.md` に工程3/4 CLI のコマンド仕様・テスト戦略・ドキュメント更新方針を整理。
- [x] ドキュメント更新（要件・設計）
  - メモ: `docs/requirements/stages/stage-03-content-normalization.md` と `stage-04-draft-structuring.md` に CLI 連携を追記し、`docs/design/20251019-stage3-4-cli.md` を追加。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `pptx content` / `pptx outline` コマンドを追加し、`cli.py` にパイプラインヘルパー・メタ出力を実装。`rendering_ready_to_jobspec` 既存機能との整合確認済み。
- [x] テスト・検証
  - メモ: `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest` を実行し、126 件すべて成功。`tests/test_cli_content.py` / `tests/test_cli_draft.py` を新規追加。
- [x] ドキュメント更新
  - メモ: ロードマップ／README／Runbook／要件を更新し、CLI 分離方針を反映。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: Issue #218 を関連付け済み。進捗は ToDo で管理し、Issue へは書き込まない。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。`todo-auto-complete` の結果を確認し、未実行なら理由を記載。手動チェックは行わない。

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
