---
目的: PPTX 解析アナライザーを構築し、品質診断に必要な幾何・スタイル情報を収集する
関連ブランチ: feat/pptx-analyzer
関連Issue: #162
roadmap_item: RM-013 PPTX 解析アナライザー実装
---
- [ ] ブランチ作成と初期コミット
  - メモ: feat/pptx-analyzer の作成と初期差分を記録する
- [ ] 計画策定（スコープ・前提・担当の整理）
  - メモ: 解析対象項目の優先度と `grid_misaligned` など既存ルールとの接続方法を整理する
- [ ] 設計・実装方針の確定
  - メモ: PoC スクリプトで PPTX 読み取りロジックを検証し、LibreOffice / Open XML SDK の利用方針をドキュメント化する
- [ ] ドキュメント更新（要件・設計）
  - メモ: 要件・設計の合意内容を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: issue/fix 出力仕様に沿ってアナライザー本体と出力処理を実装し、スキーマ整合とエラーハンドリング方針を記録する
- [ ] テスト・検証
  - メモ: テストデータ整備や `uv run --extra dev pytest` による CLI 統合テスト結果、性能測定を残す
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issueの更新
  - メモ: メトリクスとテストデータ整備状況を #162 に反映する
- [x] PR 作成
  - メモ: PR #180 https://github.com/yurake/pptx_generator/pull/180（2025-10-14 完了）

## メモ
- RM-012 の描画強化結果と整合するよう入力スキーマの最新化を確認する。
