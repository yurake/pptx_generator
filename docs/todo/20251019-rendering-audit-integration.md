---
目的: 工程6の監査メタ拡張と Polisher/PDF 連携を統合し、生成物の信頼性を確保する
関連ブランチ: 未作成
関連Issue: #219
roadmap_item: RM-026 レンダリング監査統合
---

- [ ] ブランチ作成と初期コミット
  - メモ: `feat/rendering-audit-integration` を想定。main から切り、初期コミットで ToDo を追加する。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: Approval-First 方針に従い、ユーザー承認済みメッセージ ID を記録する。
- [ ] 設計・実装方針の確定
  - メモ: 監査メタ項目と Polisher 実行フローの整理案をまとめる。
- [ ] ドキュメント更新（要件・設計）
  - メモ: stage-06 要件および関連設計ドキュメントの追補を検討する。
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: 軽量整合チェックルール、監査ログ拡張、Polisher/PDF 連携の統合を実装する。
- [ ] テスト・検証
  - メモ: CLI 統合テストで `pptx render --polisher --export-pdf` シナリオを確認し、ログ差分を検証する。
- [ ] ドキュメント更新
  - メモ: 実装結果と運用手順を docs 配下へ反映する。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: 対応する Issue 番号を確認でき次第更新する。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録し、todo-auto-complete の結果を確認する。

## メモ
- 計画フェーズでは LibreOffice / Polisher 実行環境確認手順も整理する。
