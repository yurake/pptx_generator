---
目的: CODEOWNERS を設定し、@yurake の承認を必須化する
関連ブランチ: chore-codeowners
関連Issue: #295
roadmap_item: RM-000 ガバナンス整備
---

- [x] ブランチ作成と初期コミット
  - メモ: chore-codeowners を main から作成。初期コミットは未実施。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan
    - 対象整理（スコープ、対象ファイル、前提）: `.github` 配下の CODEOWNERS 設定を確認し、存在しない場合は追加する。
    - ドキュメント／コード修正方針: `.github/CODEOWNERS` を新規作成し、全ファイルに対して `@yurake` を必須レビュワーとして記載。背景と記録を `docs/notes` に残す。
    - 確認・共有方法（レビュー、ToDo 更新など）: この ToDo を更新し、PR 説明にも Plan 承認情報を記載。GitHub 上で CODEOWNERS 動作を確認予定。
    - 想定影響ファイル: `.github/CODEOWNERS`, `docs/notes/*`
    - リスク: パターン設定ミスにより必須レビュワーが適用されない可能性。
    - テスト方針: 自動テストなし。GitHub 上で CODEOWNERS が要求されることを確認。
    - ロールバック方法: `.github/CODEOWNERS` と関連ドキュメントを削除する。
    - 承認メッセージ ID／リンク: (このチャットでのユーザー承認「ok」)
- [x] 設計・実装方針の確定
  - メモ: CODEOWNERS を単一エントリで管理し、`*` へ @yurake を割り当てる方針で確定。
- [x] ドキュメント更新（要件・設計）
  - メモ: 今回の対応では要件・設計ドキュメントの追記は不要と判断し、確認のみ実施。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `.github/CODEOWNERS` を新規作成し、全ファイルに @yurake を設定。
- [x] テスト・検証
  - メモ: 設定ファイルのみのため自動テストは未実施。GitHub 上で CODEOWNERS のレビュー要求が出ることをもって確認する。
- [x] ドキュメント更新
  - メモ: `docs/notes/20251117-codeowners.md` に対応内容を記録。その他カテゴリは今回対象外。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: #295 を関連 Issue として設定済み。
- [x] PR 作成
  - メモ: PR #296

## メモ
