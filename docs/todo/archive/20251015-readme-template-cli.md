---
目的: README に工程1 テンプレ準備 CLI 利用手順を追記する
関連ブランチ: docs/readme-template-cli
関連Issue: #190
roadmap_item: RM-019 CLI ツールチェーン整備
---

- [x] ブランチ作成と初期コミット
  - メモ: docs/readme-template-cli ブランチを作成し、README 更新用の初期コミットを実施済み。
- [x] 計画策定（スコープ・前提・担当の整理）
  - メモ: 2025-10-15 ユーザー承認済み（チャット返信 "ok"）
- [x] 設計・実装方針の確定
  - メモ: README 工程1で紹介する CLI フローとテンプレ要件を整理済み。
- [x] ドキュメント更新（要件・設計）
  - メモ: 対象外（README のみ更新で要件・設計ドキュメントに変更なし）。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: README.md にテンプレリリース CLI 手順を追記し、サンプル spec とテンプレート整合のためテストを更新。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest` および `uv run --extra dev pytest tests/test_cli_integration.py` を実行。
- [x] ドキュメント更新
  - メモ: 追加更新は不要と判断（README 以外の整合を確認）。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issueの更新
  - メモ: Issue #190 への進捗コメントは今後対応。
- [x] PR 作成
  - メモ: PR #192 https://github.com/yurake/pptx_generator/pull/192（2025-10-16 完了）

## メモ
- README の工程2 記述とスタイルを揃えることを意識する
