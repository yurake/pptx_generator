---
目的: README を最新仕様に合わせてリファクタリングし、抜け漏れのない案内に整備する
関連ブランチ: docs/readme-refactor
関連Issue: #181
roadmap_item: RM-019 CLI ツールチェーン整備
---

- [x] ブランチ作成と初期コミット
  - メモ: docs/readme-refactor を作成済み。初期コミットは README リファクタリング後に実施予定。
- [x] 計画策定（スコープ・前提・担当の整理）
  - メモ: 2025-10-12 ユーザー承認済み（本チャットログ）。抜け漏れ精査とアーキ概要との整合を対象とする。
- [x] 設計・実装方針の確定
  - メモ: README 章構成（環境要件・工程別ガイド・開発ガイドライン等）を決定し、`docs/notes/20251012-readme-refactor.md` に整理。
- [x] ドキュメント更新（要件・設計）
  - メモ: 今回は README 中心のため要件・設計ドキュメントに変更なし。確認のみ実施し差分なしを記録。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: README を再構成し、工程別の手順・コマンドリファレンス・開発者向け情報を追記。サンプルコマンドのパスを最新仕様に合わせて調整。
- [x] テスト・検証
  - メモ: ドキュメントのみの更新のため自動テストは未実施。コマンド記述の整合性を手動確認。
- [x] ドキュメント更新
  - メモ: README の改訂と検討メモ（`docs/notes/20251012-readme-refactor.md`）の追加を完了。ユーザー向け概要とプレゼン仕様 JSON の説明を追記済み。工程表に入力列を追加し、重複表現を整理。その他カテゴリは今回は変更なし。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issueの更新
  - メモ: Issue #181 に対し、PR 作成と README 改訂の進捗コメントを投稿済み。PR 本文に Close #181 を記載。
- [x] PR 作成
  - メモ: PR #182 https://github.com/yurake/pptx_generator/pull/182（2025-10-15 完了）

## メモ
- README リファクタリングの検討内容は `docs/notes/20251012-readme-refactor.md` に記録済み。
