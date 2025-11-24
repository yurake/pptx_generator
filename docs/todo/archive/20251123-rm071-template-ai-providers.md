---
目的: RM-071 Template AI マルチプロバイダ対応 — Stage1 の Template AI で Azure OpenAI / Anthropic / Bedrock 等を利用可能にする
関連ブランチ: feat/rm071-template-ai-providers
関連Issue: #302
roadmap_item: RM-071 Template AI マルチプロバイダ対応
---

- [x] ブランチ作成と初期コミット
  - メモ: 2025-11-23 `origin/main` から `feat/rm071-template-ai-providers` を作成。本ノート追加を初期コミットに含める。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: Template AI クライアント（`src/pptx_generator/template_ai/client.py`）を Content/Layout AI と同じプロバイダ構成に拡張し、policy / diagnostics / ドキュメントを更新する。既存の `mock` / `openai` は互換維持。
    - ドキュメント／コード修正方針: 共通 LLM クライアントを抽象化し、Azure OpenAI→Anthropic→Bedrock の順に対応を追加。README・requirements・design に設定手順を追記し、`config/template_ai_policies.json` の schema を調整する。
    - 確認・共有方法（レビュー、ToDo 更新など）: Plan 承認、ノート更新、PR コメントで進捗報告。`docs/notes/20251123-template-ai-provider-expansion.md` に決定事項を追記。
    - 想定影響ファイル: `src/pptx_generator/template_ai/client.py`, 共通 LLM クライアントモジュール, `config/template_ai_policies.json`, `docs/design/stages/stage-01-template-pipeline.md`, `README.md`, `tests/test_template_ai.py` ほか。
    - リスク: プロバイダ間の応答形式差異、既存環境変数との衝突、Azure/Anthropic SDK の依存追加。
    - テスト方針: 単体テスト（モック）でプロバイダ解決を検証、Azure など外部依存は環境変数を用いたスキップ条件付きテストを整備。既存回帰テストを実行。
    - ロールバック方法: Template AI クライアントの変更をリバートし、policy / ドキュメントを元に戻す。
    - 承認メッセージ ID／リンク: 2025-11-23 ユーザー承認（チャット「ok」）
- [x] 設計・実装方針の確定
  - メモ: 共通クライアント設計と設定項目の洗い出しを `docs/notes/20251123-template-ai-provider-expansion.md` に反映し、ユーザー承認済み。
- [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - メモ: 上記ノートに決定事項を追記し、チャットで共有（2025-11-23 "ok"）。
- [x] ドキュメント更新（要件・設計）
  - メモ: Template AI プロバイダ拡張後、要件／設計ドキュメントで利用可能なプロバイダと環境変数を更新する。
-  - [x] docs/requirements 配下
-  - [x] docs/design 配下
- [x] 実装
  - メモ: Template AI クライアントをマルチプロバイダ対応へリファクタリングし、Azure/AWS/Anthropic クラスを追加。
- [x] テスト・検証
  - メモ: `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/test_template_ai.py` を実行し 3 件成功。
- [x] ドキュメント更新
  - メモ: README と Stage1 設計・要件ドキュメントを更新し、ロードマップへ RM-071 を追加。runbook は影響なしのため未更新。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
    - メモ: 今回の変更では runbook への追記が不要なため、該当なしとして完了。
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: Issue #302 を参照する。
- [x] チェックリスト整合確認
  - メモ: ドキュメント更新チェックなど未チェック箇所が残っていないことを確認。
- [x] PR 作成
  - メモ: PR #303 https://github.com/yurake/pptx_generator/pull/303（2025-11-23 完了）

## メモ
- Plan 承認後に実装へ着手する。
