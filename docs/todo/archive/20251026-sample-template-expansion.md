---
目的: samples/templates/templates.pptx のページパターン拡充と samples/ 配下のバリエーション追加
関連ブランチ: feat/rm043-sample-template-expansion
関連Issue: #241
roadmap_item: RM-043 サンプルテンプレ拡充
---

- [x] ブランチ作成と初期コミット
  - メモ: `feat/rm043-sample-template-expansion` を作成し、コミット `docs(todo): add rm043 sample template expansion` を作成済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: ユーザー承認 ID: チャット返信「ok」（2025-10-26）。計画内容は 50 ページ拡充とサンプル／テスト整合方針。
- [x] 設計・実装方針の確定
  - メモ: docs/notes/20251026-rm043-sample-template-plan.md にカテゴリ別レイアウト案、アンカー仕様、テスト工程、テンプレ編集指示書を整理済み（2025-10-26）。
- [x] ドキュメント更新（要件・設計）
  - メモ: 追加検討が必要な場合は要件/設計ドキュメントへの反映可否を記録する
- [x] docs/requirements 配下
- [x] docs/design 配下
- [x] 実装
  - メモ: 2025-10-31 テンプレ矢印PH化・背景命名整理、`samples/json` 各種更新、テストコード反映まで完了（`sample_jobspec.json` が 50 ページ構成を保持）。
- [x] テスト・検証
  - メモ: `UV_CACHE_DIR=.uv-cache uv run pptx layout-validate --template samples/templates/templates.pptx --output .pptx/validation/rm043` / `UV_CACHE_DIR=.uv-cache uv run pptx gen samples/json/sample_jobspec.json --template samples/templates/templates.pptx --output .pptx/gen/rm043 --emit-structure-snapshot` / `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/test_renderer.py tests/test_cli_integration.py` を実施、warnings=0 を確認。
- [x] ドキュメント更新
  - メモ: 影響ドキュメントと更新内容を列挙する
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
    - メモ: 2025-10-31 現行記載を確認し、追加変更は不要と判断。
- [x] 関連Issue 行の更新
  - メモ: Issue 作成後に番号を反映する
- [x] PR 作成
  - メモ: PR #245 https://github.com/yurake/pptx_generator/pull/245（2025-10-31 完了）

## メモ
- 2025-10-31: 作業再開。テンプレート検証・サンプル拡張を順次実施予定。
- 計画段階でのみ完了とする場合は判断者・判断日・次のアクション条件を追記する
