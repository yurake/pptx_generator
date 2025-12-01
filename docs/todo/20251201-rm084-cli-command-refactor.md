---
目的: RM-084 CLI/Pipeline リファクタビリティ向上 - `cli.py` コマンド群の責務分離
関連ブランチ: chore/rm084-cli-refactorability
関連Issue: #344
roadmap_item: RM-084 CLI/Pipeline リファクタビリティ向上
---

- [x] ブランチ作成・初期コミット・push
  - メモ: 既存ブランチ `chore/rm084-cli-refactorability` を継続利用し、CLI 全体の分割作業を進める予定。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan を転記する。
    - 対象整理（スコープ、対象ファイル、前提）: `src/pptx_generator/cli.py` に定義されている主要コマンド（`gen`, `prepare`, `outline`, `compose`, `mapping`, `template`, `tpl-extract`, `layout-validate`, `tpl-release`）のうち、未分離のものを `cli_handlers/` 配下へ移行し、`cli.py` は Click コマンド定義とハンドラ委譲に限定する。既存の引数・メッセージ・exit code は維持する。
    - ドキュメント／コード修正方針: コマンドごとにモジュール（例: `cli_handlers/outline.py`, `cli_handlers/compose.py` 等）を追加し、共通ユーティリティを `cli_handlers/common.py`（仮）へ整理する。設計メモに完了状況を追記する。
    - 確認・共有方法（レビュー、ToDo 更新など）: コマンドを移行するたびにテスト結果を記録し、差分概要を ToDo と PR に反映する。
    - 想定影響ファイル: `src/pptx_generator/cli.py`, 新設ハンドラ群, `tests/cli/*`, `tests/integration/test_cli_generate_pipeline_flow.py`, `docs/notes/rm084-refactorability-assessment.md`, 本 ToDo。
    - リスク: 出力やログメッセージの変更による回帰、共通ヘルパーの依存破綻。
    - テスト方針: コマンドごとの既存テストを実行しつつ、最終的に `uv run --extra dev pytest` で全体確認。
    - ロールバック方法: コマンドごとにコミットを分けることで revert しやすい構成とする。
    - 承認メッセージ ID／リンク: ユーザー返信「ok」（2025-12-01）。
- [x] 設計・実装方針の確定
  - メモ: Plan 承認後に詳細方針を追記する。
    - 2025-12-01 Codex CLI: `prepare` コマンド整理案（ドラフト）
      - `cli_handlers/prepare.py` は config 正規化、静的コンテキスト解決、AI 実行、成果物書き出しが 1 関数 (`run_prepare_command`) に集中しており（同ファイル 78-193 行）、責務分離と再利用性に課題。
      - `_StaticPrepareContext`（同 196-205 行）と `_resolve_static_context`（同 208-330 行）を公開 API 化し、`resolve_static_context` (+ dataclass `PrepareStaticContext`) へ改称。静的モード専用チェック群を専用モジュール/クラスに移し、CLI 以外からも再利用できるようにする。
      - 出力ファイル定義・書き出しを `PrepareCommandArtifacts`（仮称）クラスへ分離し、`prepare_card.json` 等のパス構築と `dump_json` 呼び出しをメソッド化。`run_prepare_command` は orchestrator 実行と結果整形に専念させ、副作用をテストしやすくする。
      - CLI 側 (`src/pptx_generator/cli.py:335-368`) は `prepare` コマンドの引数検証後に `build_prepare_config()`（新規ヘルパー）で `PrepareCommandConfig` を生成し、メッセージ出力や exit code 変換を薄いラッパーとして保持。将来的に API 化・他ツール連携しやすい構造へ刷新する。
      - 追加テスト: (1) `resolve_static_context` 単体テストで jobspec 不備や manifest 不整合を網羅。(2) `PrepareCommandArtifacts` 用のファイル生成スナップショットテスト。(3) CLI 回帰テストは既存 `tests/cli/test_cli_prepare_stage_flow.py` をベースに dynamic/static ケースを維持。
      - ドキュメント: `docs/design/cli/cli-command-reference.md` に prepare ハンドラ分離と新 API 公開範囲を追記し、ToDo 完了時に整理メモを `docs/notes/rm084-refactorability-assessment.md` へ反映。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
    - 2025-12-01 Codex CLI: `docs/notes/rm084-refactorability-assessment.md` に prepare 再編内容を追記済み。
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: コマンド分割の進捗と残タスクを記録する。
    - 2025-12-01 Codex CLI: `outline`/`mapping` コマンドのハンドラ分離と `cli_handlers/{common,mapping,outline}.py` 作成、`cli.py` は委譲と互換ラッパ維持に整理。
    - 2025-12-01 Codex CLI: `tpl_release` とリリース関連ヘルパーを `cli_handlers/template_release.py` へ移管し、`template`/`tpl-release` コマンドは薄い委譲に刷新。
    - 2025-12-01 Codex CLI: テンプレート抽出ロジックを `cli_handlers/template_extraction.py` へ移動し、`template`/`tpl-extract` から委譲する構成に変更。
    - 2025-12-01 Codex CLI: `gen`/`compose`/`mapping`/`template`/`tpl-extract`/`layout-validate` を新設ハンドラ（`cli_handlers/{rendering,compose,mapping,template_commands,layout_validation}.py`）へ移管し、`cli.py` から互換ラッパを削除。対応テストの参照先も新モジュールに更新。
    - 2025-12-01 Codex CLI: LLM ログ設定とファイルロギング初期化を `cli_handlers/common.py` へ移設し、未使用ヘルパー（`_run_content_approval_pipeline` 等）を削除。`tpl-release` コマンドは `TemplateReleaseCommandConfig` を介して実装を統一。
    - 2025-12-01 Codex CLI: `prepare` コマンドの静的モード正規化を `resolve_static_context`（公開 API）へ分離し、成果物書き出しを `PrepareCommandArtifacts` で一元化。CLI は `build_prepare_config` で設定生成のみに専念する構成へ変更。
    - 2025-12-01 Codex CLI: `PrepareCommandArtifacts`／`resolve_static_context` 新設と既存 CLI ラッパ更新を実装。
    - 2025-12-02 Codex CLI: `prepare` コマンドの Click 定義を `cli_commands/prepare.py` へ移設し、`cli.py` はコマンド登録のみを担当。
    - 2025-12-02 Codex CLI: `template` コマンドも `cli_commands/template.py` へ移設し、テンプレ系オプションを共通化。
- [x] テスト・検証
  - メモ: 実施テストと結果を記載する。
    - 2025-12-01 Codex CLI: `uv run --extra dev pytest tests/cli/test_cli_outline_generation.py` / `uv run --extra dev pytest tests/integration/test_cli_generate_pipeline_flow.py` いずれも成功。
    - 2025-12-01 Codex CLI: `uv run --extra dev pytest tests/cli/test_cli_static_prompt_templates.py tests/cli/test_cli_mapping_pipeline_config.py tests/integration/test_cli_generate_pipeline_flow.py` 成功（委譲モジュール化後の回帰確認）。
    - 2025-12-01 Codex CLI: `uv run --extra dev pytest tests/cli/test_cli_prepare_stage_flow.py tests/cli/test_cli_static_prompt_templates.py tests/cli/test_cli_logging_configuration.py` 成功（prepare ハンドラ再編の回帰確認）。
- [x] ドキュメント更新
  - メモ: 変更点の影響を整理し、不要の場合も理由を記載する。
  - [x] docs/roadmap 配下（影響なしのため変更不要 / 2025-12-01 確認）
  - [x] docs/requirements 配下（prepare API 公開は既存要件と整合、更新不要）
  - [x] docs/design 配下（`docs/design/cli/cli-command-reference.md` に新構成を追記済み）
  - [x] docs/runbook 配下（運用手順への影響なしを確認）
  - [x] README.md / AGENTS.md（変更不要）
- [x] 関連Issue 行の更新
  - メモ: Issue 番号更新は必要に応じて実施する。
- [x] チェックリスト整合確認
  - メモ: 子タスク完了後に親タスクの状態を確認する。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録し、ワークフロー異常時は理由を残す。

## メモ
- まずは `outline` コマンドから着手し、他コマンドは差分が大きくなりすぎないよう段階的に移行する予定。
- `prepare` コマンドは既存ハンドラを利用中だが、`_load_prompt_overrides` など private API の取扱いをどう公開化するか要検討。
- `cli.py` に残る内容生成・Blueprint 関連ヘルパーの移設方針を検討し、pipeline 側との責務分離を進める。
