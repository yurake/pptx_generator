---
目的: RM-082 Prepare AI パッケージ再編
関連ブランチ: feat/rm082-prepare-ai-package
関連Issue: #329
roadmap_item: RM-082 Prepare AI パッケージ再編
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ `feat/rm082-prepare-ai-package` を作成し、コミット `refactor(prepare): extract ai modules into subpackage`（933d3b9）を作成して push 済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 対象整理（スコープ、対象ファイル、前提）: Stage2 のうち生成 AI に関わる実装（`prepare/orchestrator.py`, `prepare/llm_client.py`, `prepare/prompts.py`）を新設する `pptx_generator.prepare_ai` サブパッケージへ移設し、`pptx_generator.prepare` にはステージ共通モデル (`models.py`, `policy.py`, `source.py`) を残す。CLI や既存コードからの import は互換ラッパーで保持する。  
    ドキュメント／コード修正方針: 新ディレクトリを追加し、旧モジュールは薄いラッパーへ変更。`__init__.py` の公開 API を `prepare_ai` 由来へ向け直し、`docs/design/stage-02-prepare.md` 等で構成図を更新。`docs/policies/github-label-governance.md` に `prepare_ai` を追記。  
    確認・共有方法: 変更後の差分を ToDo に反映し、Plan 承認メッセージ（ユーザー「ok」 2025-11-27）を記録。必要箇所は docs で更新内容を明記。  
    想定影響ファイル: `src/pptx_generator/prepare/__init__.py`, `src/pptx_generator/prepare/{orchestrator,llm_client,prompts}.py`, 新規 `src/pptx_generator/prepare_ai/**`, `docs/design/stages/stage-02-prepare.md`, `docs/policies/github-label-governance.md`, 関連テスト。  
    リスク: モジュール移設に伴う循環 import・互換パス崩れ・テストの import 失敗。互換ラッパーと `__all__` を整備し検出。  
    テスト方針: `uv run --extra dev pytest tests/test_cli_prepare.py tests/test_prepare_llm_client.py`。  
    ロールバック方法: 移設コミットを撤回し、旧 `prepare` ディレクトリ構成へ戻す。
- [x] 設計・実装方針の確定
  - メモ: `pptx_generator.prepare_ai` を新設し、オーケストレーター／LLM クライアント／プロンプトを移設。`pptx_generator.prepare` ではモデル・ポリシー・ソースを保持しつつ、新規サブパッケージのシンボルを互換ラッパーで再公開する方針で確定。CLI からは新パッケージを直接参照する。
- [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - メモ: 今回は ToDo メモ内で方針を完結に共有済み。追加の notes は不要と判断。
- [x] ドキュメント更新（要件・設計）
  - メモ: docs/requirements 配下はステージ仕様に影響がないため変更不要と判断。docs/design 配下は Stage2 設計書の構成表とワークフローに `prepare_ai` 追記済み。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `src/pptx_generator/prepare_ai/` を追加し、`orchestrator.py`/`llm_client.py`/`prompts.py` を移設。既存 `prepare/**` には互換ラッパーを配置し、CLI の import を `prepare_ai` へ更新。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_cli_prepare.py tests/test_prepare_llm_client.py` を実行し全件成功。
- [x] ドキュメント更新
  - メモ: docs/roadmap は RM-082 を追加済み。docs/requirements は今回の構成変更で仕様差分なしと確認。docs/design は Stage2 設計書を更新済み。docs/runbook と README/AGENTS は影響なし（名称・手順変更が発生しないことを確認）。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 関連 Issue を作成次第更新。
- [x] チェックリスト整合確認
  - メモ: 子タスクのチェック状態を再確認し、親タスクの整合を確認済み。
- [x] PR 作成
  - メモ: PR #330 https://github.com/yurake/pptx_generator/pull/330（2025-11-27 完了）

## メモ
- 
