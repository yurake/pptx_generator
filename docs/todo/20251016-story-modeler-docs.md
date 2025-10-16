---
目的: 工程3でストーリー要素を取り込むための企画・要件・設計ドキュメントを整備し、RM-005 の実装準備を整える
関連ブランチ: docs/rm005-story-modeler
関連Issue: #196
roadmap_item: RM-005 プレゼンストーリーモデラー
---

- [x] ブランチ作成と初期コミット
  - メモ: `docs/rm005-story-modeler`（仮）ブランチでドキュメント素案を管理する
- [x] 計画策定（スコープ・前提・担当の整理）
  - メモ: 企画〜要件〜設計ドキュメントのみ対象とし、実装は別タスク。対象ファイルは stage-03 要件、RM-005 ロードマップ、設計資料（docs/design/配下）とする。
- [x] 設計・実装方針の確定
  - メモ: ストーリーフェーズ分類と `story_outline.json` スキーマ草案をレビュー可能な形にまとめる（docs/design/rm005-story-modeler.md 参照）
- [x] ドキュメント更新（要件・設計）
  - メモ: stage-03 要件差分と工程4連携を整理し、迷う点はユーザーへ相談した結果を残す
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: 本タスクはドキュメント整備のみのため、実装は対象外として完了扱いとする
- [x] テスト・検証
  - メモ: ドキュメントレビュー観点（整合性チェックリスト）を `docs/qa/story-outline-review.md` に記録
- [x] ドキュメント更新
  - メモ: ロードマップ・要件・設計の整合最終チェックを完了済み。運用手順を Runbook / README / AGENTS に反映
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [ ] 関連Issueの更新
  - メモ: Issue 発行後は進捗コメントと承認履歴を更新する
- [ ] PR 作成
  - メモ: PR テンプレートに対象ドキュメントとユーザー承認メッセージを記録する

## メモ
- `stage-03-content-normalization` のストーリー要素追記は本タスクで実施する。
- `story_outline` の仕様合意後に工程4/5の ToDo を見直し、必要な連動タスクを洗い出す。
- RM-024 にて `draft_approved.json` スキーマ拡張と UI 反映のフォローアップを実施する。
