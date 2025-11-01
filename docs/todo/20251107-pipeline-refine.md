---
目的: 工程2〜6の再設計準備（ジョブスペック雛形生成とコマンド整理）の要件・ロードマップ整理
関連ブランチ: docs/pipeline-refine-plan
関連Issue: 未作成
roadmap_item: RM-TBD パイプライン再設計準備
---

- [ ] ブランチ作成と初期コミット
  - メモ: 必ず main から分岐。ブランチ名・初期コミット内容を記録する
- [ ] main 取り込みと内容マージ
  - メモ: 2025-11-07 `docs/pipeline-refine-plan` で `git pull --rebase origin main` 実施済み。競合なし
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: Approval-First の承認ログを記載。現行ドキュメント整備完了後に着手する前提を整理する
- [ ] 設計・実装方針の確定
  - メモ: 工程2〜5 の責務境界と CLI 仕様変更案をまとめる
- [ ] ドキュメント更新（要件・設計）
  - メモ: 更新対象・保留点を記録する
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] main 取り込みと内容マージ
  - メモ: ブランチ作業開始前に最新 main を取り込み、競合解消の履歴を記録する
- [ ] 実装
  - メモ: 本ブランチでは RM 切り出しとドキュメント更新のみ実施。個別 RM の実装は別ブランチで対応する
- [ ] テスト・検証
  - メモ: ドキュメント整合性チェックやツール出力確認を記載する
- [ ] ドキュメント更新
  - メモ: `docs/notes/20251107-stage2-jobspec-overview.md` のマージ後再確認と更新内容を記録する
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: Issue 番号確定後にフロントマターを更新する
- [ ] PR 作成
  - メモ: PR 番号・URL を記録。todo-auto-complete が未動作の場合のみ理由を記載する

## メモ
- 工程4+5 のラッパーコマンド、`tpl-extract --validate` 相当のオプション、`pptx gen` スコープ変更などのアイテムは個別 RM として切り出し、後続ブランチで実装する計画。
