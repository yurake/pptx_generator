---
目的: `pptx mapping` / `pptx render` の分離と監査性向上を実現する
関連ブランチ: feat/rm037-pipeline-decouple
関連Issue: 未作成
roadmap_item: RM-037 パイプライン疎結合 CLI 再設計
---

- [ ] ブランチ作成と初期コミット
  - メモ: `feat/rm037-pipeline-decouple` を `main` から作成済み。初期コミットは未実施。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: 承認取得メッセージを記録予定
- [ ] 設計・実装方針の確定
  - メモ: CLI 分割時の互換性確認ポイントを整理する
- [ ] ドキュメント更新（要件・設計）
  - メモ: 設計メモの更新要否を検討する
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: サブコマンド実装とログ拡張を想定
- [ ] テスト・検証
  - メモ: CLI 統合テストと `rendering_ready` ハッシュ検証を予定
- [ ] ドキュメント更新
  - メモ: runbook / AGENTS への反映要否を確認する
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: TLS 証明書エラーで `gh issue list` の取得ができず未調査、後で再試行する
- [ ] PR 作成
  - メモ: PR 作成時に todo-auto-complete の挙動を確認する

## メモ
- 依存テーマはすべて完了済み。CLI 分割は現行フロー維持が前提。
