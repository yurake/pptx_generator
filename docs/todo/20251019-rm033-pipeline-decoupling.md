---
目的: 工程3/4独立 CLI 化に向けた要件整理とプロトタイプ設計・実装・検証を行い、RM-033 の初動を完了させる
関連ブランチ: feat/rm033-pipeline-decoupling
関連Issue: 未作成（承認メッセージ: ユーザー 2025-10-19 指示）
roadmap_item: RM-033 パイプライン工程3/4独立化準備
---

- [ ] ブランチ作成と初期コミット
  - メモ: `feat/rm033-pipeline-decoupling` を main から作成済み。Plan 承認メッセージ（2025-10-19 ユーザー指示）をコミットログへ記録予定。初期コミットではガイド更新と ToDo 追加を含める。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: scope／影響範囲／テスト戦略／ロールバック案をまとめた Plan を提示済み。承認メッセージ ID を記録する。
- [ ] 設計・実装方針の確定
  - メモ: CLI サブコマンド構成、`rendering_ready_to_jobspec` 等のヘルパー設計、監査ログ拡張の方針を確定し、必要に応じて `docs/design/` / `docs/requirements/` を更新する。
- [ ] ドキュメント更新（要件・設計）
  - メモ: `docs/requirements/stages/` および `docs/design/` 配下に工程3/4独立化の要件・設計を追記。補足ノートを `docs/notes/` に記録。
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: `src/pptx_generator/cli.py` とパイプラインモジュールに `pptx mapping` / `pptx render` を追加し、`pptx gen` からの呼び出しを再構成する。`rendering_ready_to_jobspec` 等のヘルパーを実装。
- [ ] テスト・検証
  - メモ: `uv run --extra dev pytest`、統合テストに `pptx mapping` → `pptx render` シナリオを追加し実行する。必要に応じて手動 CLI 実行で成果物を確認。
- [ ] ドキュメント更新
  - メモ: ロードマップ・README・AGENTS 等の整合を確認し、変更点を記録。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: `gh issue list --limit 50` で該当 Issue を確認し、番号を記録。進捗は ToDo で管理し、Issue へは書き込まない。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。`todo-auto-complete` の結果を確認し、未実行なら理由を記載。手動チェックは行わない。

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
