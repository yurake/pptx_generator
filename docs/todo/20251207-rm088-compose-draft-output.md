---
目的: RM-088 compose コマンドのドラフト出力ディレクトリ仕様刷新
関連ブランチ: feat/rm088-template-slide-priority
関連Issue: 未作成
roadmap_item: RM-088 テンプレ実スライド優先抽出
---

- [x] ブランチ作成・初期コミット・push
  - メモ: feat/rm088-template-slide-priority を main から作成済み。既存タスクと共通で利用する（追加の初期コミット・push は今回不要）。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: `pptx compose` / `pptx mapping` の CLI 定義とハンドラから `--draft-output` を撤廃し、ドラフト成果物の出力先を `--output` 直下の `draft/`（例: `.pptx/compose/draft`）へ自動導出する。DraftStore を含めた stage 3 の内部処理・外部フック連携は新ディレクトリ構造を前提とする。
    - ドキュメント／コード修正方針: CLI コマンド生成・ハンドラで `draft_output` の決定ロジックを更新し、`PPTX_DRAFT_OUTPUT` など環境変数も新パスを渡す。テスト／サンプル／設計ドキュメントの `--draft-output` 言及を削除し、`<output>/draft` 自動生成前提に記述を改訂する。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo を更新し、必要に応じて `docs/notes/20251207-rm088-draft-output-discussion.md` を参照。作業完了後にユーザーへ報告。
    - 想定影響ファイル: `src/pptx_generator/cli.py`, `src/pptx_generator/cli_commands/{compose,mapping}.py`, `src/pptx_generator/cli_handlers/{compose,mapping}.py`, 関連テスト (`tests/cli/*`, `tests/integration/test_cli_generate_pipeline_flow.py`)、ドキュメント／サンプル (`docs/design/cli/cli-command-reference.md`, `docs/design/stages/stage-03-compose.md`, `src/AGENTS.md`, `samples/input/sample_spec.md` ほか)。
    - リスク: DraftStore パス更新漏れによる再実行不具合、テスト期待値更新不足、ドキュメント記述の取りこぼし。外部フック利用者への影響があるため環境変数値を確実に更新する必要がある。
    - テスト方針: `uv run --extra dev pytest tests/cli` および `tests/integration/test_cli_generate_pipeline_flow.py` を実行し、新しいディレクトリ構造で CLI が通ることを確認。必要に応じて手動で `uv run pptx compose` を実行し生成物配置を確認。
    - ロールバック方法: `--draft-output` オプションと旧デフォルト `.pptx/draft` を復元するコミットをリバートし、更新したテスト／ドキュメントを元に戻す。
    - 承認メッセージ ID／リンク: （ユーザー承認済み）
- [ ] 設計・実装方針の確定
  - メモ: Plan 承認内容を踏まえた設計・実装方針をここに記載し、ユーザー確認が必要な論点があれば列挙する。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [ ] 実装
  - メモ: 実装範囲や未対応事項があれば記載する
- [ ] テスト・検証
  - メモ: 実施したテスト内容と結果を記入する
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 探索メモ: `docs/notes/20251207-rm088-draft-output-discussion.md` に議論内容を記録済み。
