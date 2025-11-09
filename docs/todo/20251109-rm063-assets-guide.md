---
目的: `assets/` ディレクトリの運用ガイドを整備し、ブランド資産管理のルールと更新フローを明文化する
関連ブランチ: docs/rm063-assets-guide
関連Issue: #284
roadmap_item: RM-063 assets 運用ガイド整備
---

- [ ] ブランチ作成と初期コミット
  - メモ: ブランチ `docs/rm063-assets-guide` を作成済み。初期コミットは未実施。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: `assets/` 直下のガイド文書新設と、`docs/README.md`・`docs/AGENTS.md` への導線追加。既存バイナリアセットの内容変更は行わない。
    - ドキュメント／コード修正方針: `assets/README.md` を新規作成し、目的・構造・命名規則・更新手順・機微情報取り扱いを整理。関連ドキュメントへリンクを追記し重複を避ける。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo を随時更新し、Plan 承認・成果物リンクを記録。PR でレビューを取得。
    - 想定影響ファイル: `assets/README.md`, `docs/README.md`, `docs/AGENTS.md`（必要に応じて）。
    - リスク: 既存ポリシー（`docs/policies/config-and-templates.md` など）との文言不整合、将来の自動生成ワークフローとの齟齬。
    - テスト方針: ドキュメントのみのため自動テストは実施せず、リンクと Markdown の構造を目視確認。
    - ロールバック方法: 追加・更新した Markdown を `git checkout -- <path>` で差し戻す。
    - 承認メッセージ ID／リンク: ユーザー承認メッセージ「おk」（2025-11-09）
- [ ] 設計・実装方針の確定
  - メモ: 
- [ ] ドキュメント更新（要件・設計）
  - メモ: 
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: 
- [ ] テスト・検証
  - メモ: 
- [ ] ドキュメント更新
  - メモ: 
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
