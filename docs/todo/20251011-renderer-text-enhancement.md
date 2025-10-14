---
目的: レンダラーでサブタイトル・ノート・テキストボックス描画を実現し、文章要素を補完する
関連ブランチ: feat/renderer-text-enhance
関連Issue: #171
roadmap_item: RM-012 レンダラーテキスト強化
---
- [ ] ブランチ作成と初期コミット
  - メモ: feat/renderer-text-enhance の作成と初期差分を記録する
- [ ] 計画策定（スコープ・前提・担当の整理）
  - メモ: スキーマ拡張レビュー結果と subtitle/notes/textboxes の描画要件を整理する
- [ ] 設計・実装方針の確定
  - メモ: PoC を通じて描画挙動を確認し、例外処理やテスト追加計画をまとめる
- [ ] ドキュメント更新（要件・設計）
  - メモ: 要件・設計の合意内容を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: スキーマ拡張とレンダラー描画処理を実装し、subtitle/notes/textboxes のエッジケース対応を記録する
- [ ] テスト・検証
  - メモ: `uv run --extra dev pytest` などで CLI 統合テストの更新結果を残す
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issueの更新
  - メモ: #171 にスキーマ拡張とテスト計画の進捗を反映する
- [x] PR 作成
  - メモ: PR #180 https://github.com/yurake/pptx_generator/pull/180（2025-10-14 完了）

## メモ
- RM-007 のアンカー仕様と整合させ、テンプレート更新が必要な場合は `samples/templates/` を見直す。
