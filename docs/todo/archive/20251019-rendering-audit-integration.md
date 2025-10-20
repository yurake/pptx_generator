---
目的: 工程6の監査メタ拡張と Polisher/PDF 連携を統合し、生成物の信頼性を確保する
関連ブランチ: feat/rendering-audit-integration
関連Issue: #177
roadmap_item: RM-026 レンダリング監査統合
---

- [x] ブランチ作成と初期コミット
  - メモ: `feat/rendering-audit-integration` を作成し、ToDo 追加で初期コミット済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: Approval-First Plan を提示し、ユーザー承認済み（会話メッセージ参照）。
- [x] 設計・実装方針の確定
  - メモ: stage-06 要件・設計・スキーマを更新し、軽量整合チェックと監査メタ拡張の方針を反映済み。
- [x] ドキュメント更新（要件・設計）
  - メモ: stage-06 要件・設計・スキーマを更新して整合チェックと監査メタ仕様を反映済み。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `RenderingAuditStep` 追加、renderer/polisher/pdf/audit CLI を拡張し監査メタを統合。
- [x] テスト・検証
  - メモ: `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/test_cli_integration.py` 実行済み（26件成功）。
- [x] ドキュメント更新
  - メモ: 実装結果と運用手順を docs 配下へ反映済み。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: Issue #177 を紐付け済み。進捗は ToDo で管理し、Issue へは書き込まない。
- [x] PR 作成
  - メモ: PR #222 https://github.com/yurake/pptx_generator/pull/222（2025-10-20 完了）

## メモ
- 計画フェーズでは LibreOffice / Polisher 実行環境確認手順も整理する。
