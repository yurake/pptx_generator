---
目的: レイアウトスタイル設定の統一設計と運用フローを具体化する
関連ブランチ: docs/layout-style-governance
関連Issue: #161
roadmap_item: RM-011 レイアウトスタイル統一
---

- [x] ブランチ作成と初期コミット
  - メモ: docs/layout-style-governance の作成と初期差分を記録する
- [x] 計画策定（スコープ・前提・担当の整理）
  - メモ: RM-010 抽出結果を踏まえた設計レビュー内容とブランド整合性の課題を整理する
  - メモ: レイアウト設定項目とブランド整合性のギャップを洗い出す
  - メモ: docs/design/layout-style-governance.md にスキーマ設計とリスク整理を記録
- [x] 設計・実装方針の確定
  - メモ: レイアウト設定スキーマ案と CLI 反映方針、テスト更新計画を決定する
  - メモ: テーブル・チャート・画像の適用項目を洗い出し、サンプル更新計画をまとめる
  - メモ: docs/design/layout-style-governance.md でテーマ構造・コンポーネント・レイアウト設定の整合を定義
- [x] ドキュメント更新（要件・設計）
  - メモ: 要件・設計の合意内容を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: レイアウト設定スキーマとレンダラー適用処理を実装し、既存スタイル適用ロジックとの統合ポイントを記録する
  - メモ: config/branding.json を layout-style-v1 へ刷新し、src/pptx_generator/settings.py / pipeline/renderer.py を更新
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest` などで新旧レイアウトの描画差分を確認する
  - メモ: `uv run --extra dev pytest` を実行し 76 件成功を確認
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issueの更新
  - メモ: #161 へ layout-style-v1 反映報告と `uv run --extra dev pytest` 成功ログを共有するコメント案を準備済み（PR 提出時に投稿）
- [x] PR 作成
  - メモ: PR 本文ドラフト（概要・影響範囲・テスト結果）を作成済み。PR 作成後に todo-auto-complete の結果を追記する

## メモ
- RM-008/009/010 の依存状況を確認し、整合チェックリストを用意する。
- `samples/` と `docs/` の更新内容を ToDo に追記する。
