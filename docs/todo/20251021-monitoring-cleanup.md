---
目的: 監視ステップで PDF-only クリーンアップが早期 return 時も実行されるよう修正し、テストで再発防止を図る
関連ブランチ: feat/rm-032-monitoring
関連Issue: 未作成
roadmap_item: RM-032 Analyzer レンダリング監視統合
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/rm-032-monitoring を継続利用
- [x] 計画策定（スコープ・前提の整理）
  - メモ: ユーザー承認済み（このスレッド）
- [x] 設計・実装方針の確定
  - メモ: `finally` でクリーンアップを呼び出す方針とユニットテスト追加で再発防止を図る
- [ ] ドキュメント更新（要件・設計）
  - メモ: 影響があれば該当ドキュメントを更新
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [x] 実装
  - メモ: `_cleanup_pdf_only` を新設し早期 return 時も削除されるよう制御フローを整理
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_monitoring_step.py` と全体テストを実行し緑化を確認
- [ ] ドキュメント更新
  - メモ: 実施内容・結果を必要に応じ記録
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: Issue 確定後に番号を反映
- [ ] PR 作成
  - メモ: PR #226 の更新予定、ワークフロー結果を確認

## メモ
- 監視ステップ失敗時も `pdf_cleanup_pptx_path` を削除する挙動を担保するテストを追加する。
