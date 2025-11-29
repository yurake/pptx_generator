---
目的: RM-079 pptx prepare directive 拡張
関連ブランチ: feat/rm079-directives
関連Issue: #318
roadmap_item: RM-079 pptx prepare directive 拡張
---

- [x] ブランチ作成・初期コミット・push
  - メモ: feat/rm079-directives (ローカル作成、push これから)
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: static モードのみ対象とし、`src/pptx_generator/cli.py`（template / prepare）、`src/pptx_generator/prepare_ai/orchestrator.py`、`src/pptx_generator/prepare/models.py`、関連テストを更新。テンプレ抽出で `.pptx/extract/prompts/` 雛形を生成し、prepare では同フォルダの編集差分を自動適用する。
    - 実装方針: ① template stage でスライド単位の Markdown 雛形を生成（不変ブロック＋ user-editable ブロックを明示、既存ファイルは保持）。② prepare static で雛形フォルダを探索し、編集済みスライドのみ LLM プロンプトへ注入しつつ `prepare_ai_log.json` / `ai_generation_meta.json` に適用結果を記録。③ CLI・orchestrator・モデル・テストを整合させ、ユーザーメッセージと監査ログを追加する。
    - 確認・共有方法: `docs/design/cli/cli-command-reference.md` と README へ手順とマーキング方法を追記し、ToDo にテスト結果と適用例を記録。PR ではテンプレ雛形／apply のスクリーンショットと運用上の注意を添付。
    - 想定影響ファイル: `src/pptx_generator/cli.py`, `src/pptx_generator/prepare_ai/orchestrator.py`, `src/pptx_generator/prepare/models.py`, `src/pptx_generator/prepare_ai/prompts.py`, `tests/cli/test_cli_prepare_stage_flow.py`, `tests/prepare_ai/test_prepare_ai_orchestrator_flow.py`, `docs/design/cli/cli-command-reference.md`, `README.md` ほかドキュメント。
    - リスク: Markdown 雛形の書式崩れでパース失敗するリスク、未編集ファイル上書きによる誤差分消失、LLM プロンプトの肥大化。ガードとして既存ファイルは再生成しない、user-editable 節のみ抽出、エラー時はフォールバック＋警告ログで検知。
    - テスト方針: `uv run --extra dev pytest tests/cli/test_cli_prepare_stage_flow.py tests/prepare_ai/test_prepare_ai_orchestrator_flow.py` を中心に static フローと雛形適用の有無を検証。必要に応じて integration テストも追加実行。
    - ロールバック方法: CLI/オーケストレーター/モデル変更と docs 追記をまとめて revert。`.pptx/extract/prompts/` を削除し、AI メタの追加フィールドを除去する。
    - 承認メッセージ ID／リンク: ユーザー承認「ok」（本スレッド）
- [x] 設計・実装方針の確定
  - メモ: テンプレ雛形生成＋ static prepare 反映で合意済み。実装内容は `docs/notes/20251127-rm079-static-prompt-discussion.md` に整理。
- [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - メモ: 上記ノートで会話ログと決定内容を共有済み。
- [x] ドキュメント更新（要件・設計）
  - メモ: CLI リファレンス・stage 2 設計・README を更新済み。要件ドキュメントは既存記述で整合が取れているため変更不要として記録。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `cli.template` で `.pptx/extract/prompts/` を生成、`prepare` static で雛形を読み込み。`PrepareAIOrchestrator` / `PrepareGenerationMeta` / `PrepareAIRecord` に新フィールド追加。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/cli/test_cli_prepare_stage_flow.py tests/prepare_ai/test_prepare_ai_orchestrator_flow.py`
- [x] ドキュメント更新
  - メモ: CLI リファレンス、stage 2 設計、README に雛形編集フローとログ項目を追記。
  - [x] docs/roadmap 配下
    - メモ: 影響なし（既存ロードマップ項目に変更不要）。
  - [x] docs/requirements 配下（実装結果との整合再確認）
    - メモ: 要件追加なし、現行記述で整合取れているため更新不要。
  - [x] docs/design 配下（実装結果との整合再確認）
    - メモ: `docs/design/cli/cli-command-reference.md` と `docs/design/stages/stage-02-prepare.md` を更新済み。
  - [x] docs/runbook 配下
    - メモ: 運用手順の変更なし（雛形編集は CLI リファレンス記載で対応）。
  - [x] README.md / AGENTS.md
    - メモ: README の stage 概要を更新。AGENTS 系は変更不要。
- [x] 関連Issue 行の更新
  - メモ: 
- [x] チェックリスト整合確認
  - メモ: 本 ToDo の各項目と実装内容を突合。未対応は PR 作成のみ。
- [x] PR 作成
  - メモ: PR #338 https://github.com/yurake/pptx_generator/pull/338（2025-11-29 完了）

## メモ
