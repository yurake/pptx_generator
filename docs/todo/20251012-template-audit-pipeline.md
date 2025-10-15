---
目的: テンプレ資産の差分検証と受け渡しメタ生成を自動化し、工程1の品質ゲートを強化する
関連ブランチ: feat/template-audit-pipeline
関連Issue: #178
roadmap_item: RM-021 テンプレ資産監査パイプライン
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/template-audit-pipeline ブランチで初期コミットまで完了
- [x] 計画策定（スコープ・前提・担当の整理）
  - メモ: テンプレ改訂頻度とメタ保持先、ゴールデンサンプル運用方針を確認する
  - メモ: 2025-10-12 計画案（scope/impact/risks/tests/rollback）をユーザー承認済み
- [x] 設計・実装方針の確定
  - メモ: `template_release.json` スキーマ、差分レポート形式、検証ジョブ構成をまとめる
  - メモ: 2025-10-12 スキーマ仕様・サンプルを docs/design/schema に反映済み
- [x] 実装
  - メモ: release メタ生成 CLI、差分比較ロジック、通知フローを実装する
  - メモ: Golden Runner オプションとログ出力 (`golden_runs`) を追加する
  - メモ: 2025-10-12 CLI `tpl-release` にゴールデンサンプル実行と `golden_runs.json` 出力を実装済み
- [x] テスト・検証
  - メモ: ゴールデンサンプルとの突合テスト、差分検知の回帰テスト、通知疎通確認を実施する
  - メモ: 2025-10-12 `uv run pptx tpl-release` を成功／失敗ケースで実行し、出力物と exit code を確認済み
- [ ] 関連Issueの更新
  - メモ: 関連 Issue を確認し、進捗コメントと差分レポート共有方法を記録する
- [x] PR 作成
  - メモ: PR #189 https://github.com/yurake/pptx_generator/pull/189（2025-10-15 完了）

## メモ
- LibreOffice / Open XML SDK を用いた互換性検証が前提となるため、ジョブ実行環境の依存関係を整理する
