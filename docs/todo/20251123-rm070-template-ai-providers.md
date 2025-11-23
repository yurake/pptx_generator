---
目的: RM-070 Template AI マルチプロバイダ対応 — Stage1 の Template AI で Azure OpenAI / Anthropic / Bedrock 等を利用可能にする
関連ブランチ: 未作成
関連Issue: 未作成
roadmap_item: RM-070 Template AI マルチプロバイダ対応
---

- [ ] ブランチ作成と初期コミット
  - メモ: 作業開始時に `feat/rm070-template-ai-providers` を `main` から作成し、ノート追加など最小差分で初期コミットを行う。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: Template AI クライアント（`src/pptx_generator/template_ai/client.py`）を Content/Layout AI と同じプロバイダ構成に拡張し、policy / diagnostics / ドキュメントを更新する。既存の `mock` / `openai` は互換維持。
    - ドキュメント／コード修正方針: 共通 LLM クライアントを抽象化し、Azure OpenAI→Anthropic→Bedrock の順に対応を追加。README・requirements・design に設定手順を追記し、`config/template_ai_policies.json` の schema を調整する。
    - 確認・共有方法（レビュー、ToDo 更新など）: Plan 承認、ノート更新、PR コメントで進捗報告。`docs/notes/20251123-template-ai-provider-expansion.md` に決定事項を追記。
    - 想定影響ファイル: `src/pptx_generator/template_ai/client.py`, 共通 LLM クライアントモジュール, `config/template_ai_policies.json`, `docs/design/stages/stage-01-template-pipeline.md`, `README.md`, `tests/test_template_ai.py` ほか。
    - リスク: プロバイダ間の応答形式差異、既存環境変数との衝突、Azure/Anthropic SDK の依存追加。
    - テスト方針: 単体テスト（モック）でプロバイダ解決を検証、Azure など外部依存は環境変数を用いたスキップ条件付きテストを整備。既存回帰テストを実行。
    - ロールバック方法: Template AI クライアントの変更をリバートし、policy / ドキュメントを元に戻す。
    - 承認メッセージ ID／リンク: （承認取得後に記載）
- [ ] 設計・実装方針の確定
  - メモ: 共通クライアント設計と設定項目の洗い出しを `docs/notes/20251123-template-ai-provider-expansion.md` に反映し、レビューを依頼する。
- [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - メモ: 上記ノートに決定事項を追記し、ユーザーへ共有する。
- [ ] ドキュメント更新（要件・設計）
  - メモ: Template AI プロバイダ拡張後、要件／設計ドキュメントで利用可能なプロバイダと環境変数を更新する。
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: Template AI クライアントのリファクタリングと追加プロバイダ実装を行い、policy / diagnostics を更新する。
- [ ] テスト・検証
  - メモ: 単体テストと必要な統合テスト（モック実行）を追加し、`uv run --extra dev pytest` を実行して回帰を確認する。
- [ ] ドキュメント更新
  - メモ: README / runbook など利用手順を更新し、影響範囲を整理する。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: Issue 作成後に番号を反映する。
- [ ] チェックリスト整合確認
  - メモ: 子タスク完了状況を確認し、必要に応じて `[x]` 化する。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録し、todo-auto-complete の結果を確認する。

## メモ
- Plan 承認後に実装へ着手する。
