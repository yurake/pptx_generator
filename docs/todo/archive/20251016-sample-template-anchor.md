---
目的: サンプル仕様とコマンド手順をテンプレート指定必須の状態に合わせて更新し、アンカー付きテンプレでも失敗しないようにする
関連ブランチ: fix/sample-template-anchor
関連Issue: #194
roadmap_item: RM-019 CLI ツールチェーン整備
---

- [x] ブランチ作成と初期コミット
  - メモ: 2025-10-16 ブランチ fix/sample-template-anchor 作成済み。初期コミットとしてドキュメント更新と ToDo 追記を反映。
- [x] 計画策定（スコープ・前提・担当の整理）
  - メモ: 2025-10-16 ユーザー承認（チャット返信 "ok"）を取得。対象ドキュメントと検証方針を整理済み。
- [x] 設計・実装方針の確定
  - メモ: `sample_jobspec.json` を参照する手順のみテンプレート指定を追加し、アーカイブ記録には触れない方針で進める。
- [x] ドキュメント更新（要件・設計）
  - メモ: 今回は要件・設計ドキュメントに変更不要と判断し、影響なしを確認。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: AGENTS 系ガイドと `docs/qa` / `docs/notes` のコマンド例をテンプレート指定付きへ更新済み。
- [x] テスト・検証
  - メモ: `uv run pptx gen samples/json/sample_jobspec.json --template samples/templates/templates.pptx --output .pptx/gen/review-20251016` を実行し、PPTX と analysis の生成を確認。
- [x] ドキュメント更新
  - メモ: AGENTS.md / src/AGENTS.md / config/AGENTS.md / docs/qa / docs/notes を更新済み。ロードマップや要件設計への影響はなし。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issueの更新
  - メモ: Issue #194 を参照。PR #195 で PR #192 のレビューコメントを処理。
- [x] PR 作成
  - メモ: PR #195 https://github.com/yurake/pptx_generator/pull/195（2025-10-16 完了）

## メモ
- レビューコメント出典: GitHub PR #192 review thread（2025-10-16）
