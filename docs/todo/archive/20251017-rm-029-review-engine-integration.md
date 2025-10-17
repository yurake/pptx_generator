---
目的: Analyzer と Review Engine の連携仕様を整理し、issues/fixes 連携の実装方針を確定する
関連ブランチ: feat/rm-029-review-engine-integration
関連Issue: #208
roadmap_item: RM-029 Analyzer Review Engine 連携
---

- [x] ブランチ作成と初期コミット
  - メモ: 2025-10-17 main から feat/rm-029-review-engine-integration を作成し、空コミット `chore(rm-029): start review engine integration` を作成済み
- [x] 計画策定（スコープ・前提・担当の整理）
  - メモ: ユーザー承認済み Plan（Analyzer→Review Engine 変換スコープ、サポート Fix 種別、テスト戦略）を 2025-10-17 に共有
- [x] 設計・実装方針の確定
  - メモ: `AnalyzerReviewEngineAdapter` 設計（grade 算出・JSON Patch 変換・未対応 Fix 記録）を決定
- [x] ドキュメント更新（要件・設計）
  - メモ: Stage-03 設計ドキュメントへ Analyzer 連携フローを追記、ノートで進捗を更新
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `review_engine_analyzer.json` 生成処理・アダプタ・監査ログ出力・テスト追加を実装
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_review_engine_adapter.py tests/test_cli_integration.py`
- [x] ドキュメント更新
  - メモ: roadmap/requirements/runbook/README 反映を実施済み。今後は Review Engine UI への展開を別タスクで管理
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: GitHub Issue #208 と紐付け（2025-10-17）
- [x] PR 作成
  - メモ: PR #210 https://github.com/yurake/pptx_generator/pull/210（2025-10-17 完了）

## メモ
