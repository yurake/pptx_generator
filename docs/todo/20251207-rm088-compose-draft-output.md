---
目的: RM-088 compose コマンドのドラフト出力ディレクトリ仕様刷新
関連ブランチ: feat/rm088-template-slide-priority
関連Issue: #396
roadmap_item: RM-088 テンプレ実スライド優先抽出
---

- [x] ブランチ作成・初期コミット・push
  - メモ: feat/rm088-template-slide-priority を main から作成済み。既存タスクと共通で利用する（追加の初期コミット・push は今回不要）。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: `pptx compose` / `pptx mapping` の CLI 定義とハンドラから `--draft-output` を撤廃し、ドラフト成果物の出力先を `--output` 直下の `draft/`（例: `.pptx/compose/draft`）へ自動導出する。DraftStore を含めた stage 3 の内部処理・外部フック連携は新ディレクトリ構造を前提とする。
    - ドキュメント／コード修正方針: CLI コマンド生成・ハンドラで `draft_output` の決定ロジックを更新し、`PPTX_DRAFT_OUTPUT` など環境変数も新パスを渡す。テスト／サンプル／設計ドキュメントの `--draft-output` 言及を削除し、`<output>/draft` 自動生成前提に記述を改訂する。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo を更新し、必要に応じて `docs/notes/20251207-rm088-draft-output-discussion.md` を参照。作業完了後にユーザーへ報告。
    - 想定影響ファイル: `src/pptx_generator/cli.py`, `src/pptx_generator/cli_commands/{compose,mapping}.py`, `src/pptx_generator/cli_handlers/{compose,mapping}.py`, 関連テスト (`tests/cli/*`, `tests/integration/test_cli_generate_pipeline_flow.py`)、ドキュメント／サンプル (`docs/design/cli/cli-command-reference.md`, `docs/design/stages/stage-03-compose.md`, `src/AGENTS.md`, `samples/input/sample_spec.md` ほか)。
    - リスク: DraftStore パス更新漏れによる再実行不具合、テスト期待値更新不足、ドキュメント記述の取りこぼし。外部フック利用者への影響があるため環境変数値を確実に更新する必要がある。
    - テスト方針: `uv run --extra dev pytest tests/cli` および `tests/integration/test_cli_generate_pipeline_flow.py` を実行し、新しいディレクトリ構造で CLI が通ることを確認。必要に応じて手動で `uv run pptx compose` を実行し生成物配置を確認。
    - ロールバック方法: `--draft-output` オプションと旧デフォルト `.pptx/draft` を復元するコミットをリバートし、更新したテスト／ドキュメントを元に戻す。
    - 承認メッセージ ID／リンク: （ユーザー承認済み）
- [x] 設計・実装方針の確定
  - メモ: Plan を基に docs/notes/20251207-rm088-draft-output-discussion.md に設計メモを整理し参照先を示した。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: `pptx compose` / `pptx mapping` の CLI オプションから `--draft-output` を削除し、`draft_output = output_dir / "draft"` を導出するよう更新。`PPTX_DRAFT_OUTPUT` を含む環境変数と DraftStore の解決先を新構造へ合わせ、テストコード／サンプルのパスも `<output>/draft` 前提に修正。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/cli/test_cli_outline_generation.py`、`uv run --extra dev pytest tests/cli/test_cli_cheatsheet_guidance_flow.py`、`uv run --extra dev pytest tests/integration/test_cli_generate_pipeline_flow.py` を実行し、いずれも成功を確認。
- [x] ドキュメント更新
  - メモ: 主要ドキュメントを `<output>/draft` 自動生成の前提に書き換え、手順サンプルを新コマンド構成へ更新。
  - [x] docs/roadmap 配下
  - メモ: RM-088 項目の内容と差異がないため追加更新は不要と判断。
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - メモ: 要件との差分が生じていないことを確認し追記不要と判断。
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [x] チェックリスト整合確認
  - メモ: チェック済み項目の取りこぼしがないことを点検した。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 探索メモ: `docs/notes/20251207-rm088-draft-output-discussion.md` に議論内容を記録済み。
- UAT 計画（compose/mapping ドラフト出力動作確認）  
  1. `docs/todo/20251207-rm088-template-slide-priority.md` に従って静的モードの検証手順を実施し、`compose`／`mapping` が生成するドラフト成果物の配置が `<output>/draft` になっていることを確認する。  
  2. 上記 UAT の成果物 (`.pptx/uat-*/compose/draft/*`, `.pptx/uat-*/mapping/draft/*` など) をレビューし、`generate_ready.json` やメタファイルが期待する出力先に揃っているか検証。  
  3. `docs/todo/20251207-rm088-compose-draft-output.md` のタスク完了要件（テスト・ドキュメント更新含む）が満たされているかチェックし、気づきがあれば本メモに追記する。
- UAT 実行ログ  
  - `.pptx/uat-from-slide/*` 系で `compose` → `draft/` サブディレクトリ生成と `ai_generation_meta.template_source="slide"`、`generate_ready.meta.template_source="slide"` を確認。`pptx gen` 出力も `.pptx/uat-from-slide/gen` 直下に生成。  
  - `.pptx/uat-from-template/*` 系（`static_template.pptx` 使用）で同様に `draft/` サブディレクトリが自動作成され、`template_source="template"` となり、出力 PPTX は 4 ページのみ生成されることを確認。  
  - `.pptx/uat-from-template-fallback/*` を `static_slide.pptx` + `--from slide` で再実行し、ドラフト出力先が `<output>/draft` に統一されることを再確認（`template_source="slide"`）。  
  - 既定パス（`uv run pptx compose ...` のみ）でも `.pptx/compose/draft` が作成され、`pptx gen` は `.pptx/gen` を使用。  
  - 異常系テスト（テンプレパス強制削除・メタ改変）は未実施。必要になった際に追加で検証する。
