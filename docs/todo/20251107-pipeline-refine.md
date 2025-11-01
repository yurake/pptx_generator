---
目的: 工程2〜6の再設計準備（ジョブスペック雛形生成とコマンド整理）の要件・ロードマップ整理
関連ブランチ: docs/pipeline-refine-plan
関連Issue: #247
roadmap_item: RM-TBD パイプライン再設計準備
---

- [x] ブランチ作成と初期コミット
  - メモ: 2025-11-07 `docs/pipeline-refine-plan` 作成。初期コミットで note / ToDo を追加
- [x] main 取り込みと内容マージ
  - メモ: 2025-11-07 `git pull --rebase origin main` を複数回実行。競合・差分なしを確認済み（ローカルと origin 双方）
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: Approval-First の承認ログを記載。現行ドキュメント整備完了後に着手する前提を整理する
- [ ] 設計・実装方針の確定
  - メモ: 工程2〜5 の責務境界と CLI 仕様変更案をまとめる
- [ ] ドキュメント更新（要件・設計）
  - メモ: 更新対象・保留点を記録する
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: 本ブランチでは RM 切り出しとドキュメント更新のみ実施。個別 RM の実装は別ブランチで対応する
- [ ] テスト・検証
  - メモ: ドキュメント整合性チェックやツール出力確認を記載する
- [ ] ドキュメント更新
  - メモ: `docs/notes/20251107-stage2-jobspec-overview.md` のマージ後再確認と更新内容を記録する
  - [x] docs/roadmap 配下
    - メモ: 2025-11-07 RM-044〜RM-049 を追加し、工程見直し案を反映
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: Issue 番号確定後にフロントマターを更新する
- [ ] PR 作成
  - メモ: PR 番号・URL を記録。todo-auto-complete が未動作の場合のみ理由を記載する

## メモ
- 工程4+5 のラッパーコマンド、`tpl-extract --validate` 相当のオプション、`pptx gen` スコープ変更などのアイテムは個別 RM として切り出し、後続ブランチで実装する計画。
