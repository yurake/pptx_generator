---
目的: PPTX 解析アナライザーを構築し、品質診断に必要な幾何・スタイル情報を収集する
関連ブランチ: feat/pptx-analyzer
関連Issue: #162
roadmap_item: RM-013 PPTX 解析アナライザー実装
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/pptx-analyzer の作成と初期差分を記録する
- [x] 計画策定（スコープ・前提・担当の整理）
  - メモ: 解析対象項目の優先度と `grid_misaligned` など既存ルールとの接続方法を整理する
- [x] 設計・実装方針の確定
  - メモ: PoC スクリプトで PPTX 読み取りロジックを検証し、LibreOffice / Open XML SDK の利用方針をドキュメント化する
  - メモ: issue/fix 出力仕様とテストデータ準備計画を策定し、CI でのバイナリ比較方式と性能測定の仮案を記録する
- [x] ドキュメント更新（要件・設計）
  - メモ: 要件・設計の合意内容を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: issue/fix 出力仕様に沿ってアナライザー本体と出力処理を実装し、スキーマ整合とエラーハンドリング方針を記録する
- [x] テスト・検証
  - メモ: 2025-10-15 に `uv run --extra dev pytest` を実行し、86 件すべて成功（2.42s）。CLI 統合テストの通過と性能測定初期値を記録済。性能計測の追加検討は継続課題。
- [x] テストデータ整備と自動テストの追加
  - メモ: PPTX 比較ロジックと性能計測の結果を共有する
- [x] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issueの更新
  - メモ: メトリクスとテストデータ整備状況を #162 に反映する
  - [x] #162 コメント草案の確認と投稿
- [x] PR 作成
  - メモ: PR #198 https://github.com/yurake/pptx_generator/pull/198（2025-10-16 完了）

## メモ
- RM-012 の描画強化結果と整合するよう入力スキーマの最新化を確認する。
- 2025-10-15: 実装・テスト内容のメモは `docs/notes/20251015-pptx-analyzer.md` にまとめた。CLI 統合テストを完了済。性能測定の詳細検証は継続課題。
- 2025-10-17: `docs/runbooks/pptx-analyzer.md` を追加し、README と AGENTS に導線を追記。Issue #162 へのサマリ投稿草案は次の更新で整理する。
- #162 投稿草案（2025-10-17 投稿済メモ）
  - 追加: `docs/runbooks/pptx-analyzer.md`、README/AGENTS/Docs README からの導線追記
  - 確認: `analysis.json` の issue/fix 種別表、運用フロー、トラブルシューティングを整理
  - 残課題: 性能計測の詳細検証、Refiner との自動修正連携強化、通知フロー連携案の検討
