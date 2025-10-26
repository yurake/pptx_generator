---
目的: 工程3における生成AI活用フローを整備し、ユースケース別ポリシー制御と監査ログ連携を実現する
関連ブランチ: feat/rm-040-ai-orchestration
関連Issue: #242
roadmap_item: RM-040 コンテンツ生成AIオーケストレーション
---

- [x] ブランチ作成と初期コミット
  - メモ: ブランチ作成済み（feat/rm-040-ai-orchestration）。初期コミットは base が origin/main のため差分なし。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 2025-10-26 ユーザー承認済み Plan（このスレッド）を反映済み。
- [x] 設計・実装方針の確定
  - メモ: content_ai モジュール構成と CLI 拡張を docs/notes/20251026-rm-040-initial-plan.md に整理。
- [x] ドキュメント更新（要件・設計）
  - メモ: 工程3 の AI オーケストレーション追記を設計・要件へ反映。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: content_ai モジュール新設、CLI オプション追加、サンプルポリシー／ログ出力を実装。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/content_ai -q` と `uv run --extra dev pytest tests/test_cli_integration.py -k content_ai_generation -q` を完了。
- [x] ドキュメント更新
  - メモ: README を生成AIデフォルト仕様へ更新。ロードマップ／runbook 連携は別途検討。
  - [ ] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: `gh issue list --limit 50` 実行時に証明書エラー（OSStatus -26276）が発生したため未確認。解消後に更新する。
- [ ] PR 作成
  - メモ: 承認後に対応。

## メモ
- 計画策定に合わせて docs/notes/20251023-roadmap-theme-research.md の追加調査要否を判断する。
- config/content_ai_policies.json を初版作成。将来のモデル差し替え時は `model` と `safeguards` を更新予定。
- CLI は生成AIモードをデフォルト化し、プロンプトは `src/pptx_generator/content_ai/prompts.py` で ID 管理とした。非生成AIは `--content-source` / `--content-approved` 指定時のみ使用。
