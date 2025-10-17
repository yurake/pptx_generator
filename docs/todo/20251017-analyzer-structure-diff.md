---
目的: Analyzer 構造抽出結果とスナップショット差分レポートの仕様策定と実装準備
関連ブランチ: feat/rm028-analyzer-diff
関連Issue: 未作成
roadmap_item: RM-028 Analyzer 構造抽出差分連携
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/rm028-analyzer-diff を main から作成し、キックオフトラッカーをコミット済み。
- [x] 計画策定（スコープ・前提・担当の整理）
  - メモ: ユーザー承認（2025-10-17）を受領し、Plan を共有済み。
- [x] 設計・実装方針の確定
  - メモ: Analyzer スナップショット連携と diff 仕様を ToDo・ドキュメントへ反映。
- [x] ドキュメント更新（要件・設計）
  - メモ: requirements/design に Analyzer 突合要件を追加。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: Analyzer スナップショット出力と layout-validate の突合処理を実装。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_analyzer.py tests/test_layout_validation_suite.py` / `uv run --extra dev pytest tests/test_cli_integration.py` を実行。
- [x] ドキュメント更新
  - メモ: 結果と影響範囲を整理する。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 関連 Issue は未発行のため保留（対応不要）。
- [ ] PR 作成
  - メモ: PR 作成時に番号と URL を記録する。todo-auto-complete の結果も確認する。

## メモ
- 計画のみで完了とする場合は判断内容を記録する。
- docs/runbook は今回の機能では変更不要（手順差分なし）。
