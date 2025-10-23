---
目的: `pptx mapping` / `pptx render` の分離と監査性向上を実現する
関連ブランチ: feat/rm037-pipeline-decouple
関連Issue: #234
roadmap_item: RM-037 パイプライン疎結合 CLI 再設計
---

- [x] ブランチ作成と初期コミット
  - メモ: `feat/rm037-pipeline-decouple` を `main` から作成し、ToDo 追加の初期コミット (`docs(todo): add rm037 pipeline decoupling task`) を実施。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 2025-10-23 ユーザー承認（メッセージ:「ok」）を受領済み。
- [x] 設計・実装方針の確定
  - メモ: `docs/notes/20251018-pipeline-decoupling-design.md` を再確認し、監査メタ拡張と単体テスト追加を方針化。
- [x] ドキュメント更新（要件・設計）
  - メモ: 設計メモは既存ノートに追記。追加設計ドキュメントは不要と判断。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `MappingStep` の `mapping_meta` 拡張と `audit_log` のハッシュ追加、CLI 再実行テストを実装。
- [x] テスト・検証
  - メモ: `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/test_cli_integration.py tests/test_rendering_ready_utils.py`
- [x] 全テスト実行
  - メモ: `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest`
- [x] ドキュメント更新
  - メモ: requirements / notes / design / runbook を更新済み。roadmap 追記は不要と判断。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: #234 を参照（`gh issue list` は TLS エラー継続のためブラウザで確認）。
- [x] PR 作成
  - メモ: PR #236 https://github.com/yurake/pptx_generator/pull/236（2025-10-23 完了）

## メモ
- 依存テーマはすべて完了済み。CLI 分割は現行フロー維持が前提。
