---
目的: RM-079 pptx prepare directive 拡張（スライド単位入力対応）
関連ブランチ: feat/rm079-directives
関連Issue: #318
roadmap_item: RM-079 pptx prepare directive 拡張
---

- [x] ブランチ作成・初期コミット・push
  - メモ: 既存ブランチ `feat/rm079-directives` を継続利用。
- [x] 計画策定（スコープ・前提の整理）
  - メモ:
    - 対象整理（スコープ、対象ファイル、前提）: static モードの `pptx template` / `pptx prepare`。`src/pptx_generator/cli.py`、`src/pptx_generator/prepare_ai/orchestrator.py`、`src/pptx_generator/prepare/models.py`、関連テスト・ドキュメントを更新する。
    - ドキュメント／コード修正方針: `.pptx/slide_inputs.md` を template 実行時に生成し、`01_system-layout` など雛形と同じ命名で入力ファイルを割り当てる。全スライド分が記載されていれば `pptx prepare` の `<data file path>` を省略可。未指定スライドがある場合はエラーとする。
    - 確認・共有方法（レビュー、ToDo 更新など）: Plan 承認後に ToDo へ転記し、必要に応じて docs/notes へ仕様メモを追加する。進捗は本 ToDo に記録。
    - 想定影響ファイル: `src/pptx_generator/cli.py`, `src/pptx_generator/prepare_ai/orchestrator.py`, `src/pptx_generator/prepare/models.py`, `tests/cli/test_cli_static_prompt_templates.py`, README, `docs/design/cli/cli-command-reference.md`, `docs/design/stages/stage-02-prepare.md` など。
    - リスク: マニフェスト記述ミスやファイル欠落によるエラー、既存利用者への互換性影響。
    - テスト方針: `uv run --extra dev pytest` に加え、CLI で `.pptx/slide_inputs.md` を使ったケース（省略可/未指定エラー）を手動確認。
    - ロールバック方法: マニフェスト生成・読込・ログ追記のコミットを revert し旧挙動へ戻す。
    - 承認メッセージ ID／リンク: ユーザー承認（このスレッドの直近メッセージ）
- [x] 設計・実装方針の確定
  - メモ: static テンプレ抽出時に `.pptx/extract/prompts/01_*.md` と `.pptx/slide_inputs.md` を生成し、prepare 実行時は前者の差分適用と後者のマニフェスト解決でスライド別入力を切り替える方針に確定。
- [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - メモ: `docs/notes/20251127-rm079-static-prompt-discussion.md` を確認し、今回の仕様が合意内容と一致していることを再確認済み。
- [x] ドキュメント更新（要件・設計）
  - メモ: `docs/design/cli/cli-command-reference.md`, `docs/design/stages/stage-02-prepare.md` に雛形生成フローとスライド入力マニフェストの利用手順を追記。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `src/pptx_generator/cli.py`, `src/pptx_generator/prepare/models.py`, `src/pptx_generator/prepare_ai/orchestrator.py` でマニフェスト生成・読込・ログ出力を追加し、テンプレ抽出時の案内ログを出力するよう調整。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/cli/test_cli_prepare_stage_flow.py tests/cli/test_cli_static_prompt_templates.py` と `uv run --extra dev pytest` を実行し全件成功（`coverage.xml` 更新済み）。
- [x] ドキュメント更新
  - メモ: README と設計資料の内容を最新仕様へ更新。その他カテゴリは今回対象外のため差分なし。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: GitHub API 経由でコメント投稿を試行したが 404 応答で失敗。ユーザーに確認予定。
- [x] チェックリスト整合確認
  - メモ: `uv run python scripts/lint_todo_completion.py` を実行し、残存チェックに問題がないことを確認。
- [x] PR 作成
  - メモ: `feat/rm079-directives` ブランチへコミット反映済み。リモート更新は権限者の再 push 後に PR #338 を更新予定。

## メモ
