---
目的: Refiner の自動補正を拡張し、Open XML SDK ベースの仕上げ工程を統合する
関連ブランチ: feat/polisher-integration
関連Issue: #160
roadmap_item: RM-014 自動補正・仕上げ統合
---
- [ ] ブランチ作成と初期コミット
  - メモ: feat/polisher-integration の作成と初期差分を記録する
- [ ] 計画策定（スコープ・前提・担当の整理）
  - メモ: 自動補正ポリシーの適用範囲と監査ログ対応、承認取得済みメッセージを整理する
- [ ] 設計・実装方針の確定
  - メモ: Open XML SDK 連携アーキテクチャと CLI 連携ポイントを確定する
- [ ] ドキュメント更新（要件・設計）
  - メモ: 要件・設計の合意内容を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: Refiner と Polisher の連携およびエラーハンドリングを実装する
- [ ] テスト・検証
  - メモ: `uv run --extra dev pytest` や .NET テストで補正結果と PDF/PPTX 品質を確認する
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issueの更新
  - メモ: 監査ログ仕様と補正ポリシーの進捗を #160 に反映する
- [x] PR 作成
  - メモ: PR #180 https://github.com/yurake/pptx_generator/pull/180（2025-10-14 完了）

## メモ
- 解析結果 (RM-013) との連携前提を明文化し、.NET 8 実行環境の要件を確認する。
