---
目的: RM-088 テンプレ実スライド優先抽出の実装に向けた準備と実装
関連ブランチ: feat/rm088-template-slide-priority
関連Issue: #392
roadmap_item: RM-088 テンプレ実スライド優先抽出
---

- [ ] ブランチ作成・初期コミット・push
  - メモ: feat/rm088-template-slide-priority を main から作成。リモートへの push は未実施。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: Stage1 静的モードに `--from {slide,template}` を追加し既定で実スライド抽出とする。後方互換は考慮しない。Stage2〜4 へ抽出ソース種別をメタとして引き継ぎ、Stage4 レンダラーは実スライド・テンプレどちらにも対応する前提で、入力テンプレはソースを混在させず一方のみ採用する。
    - ドキュメント／コード修正方針: TemplateExtractor / CLI / モデル / パイプラインを改修し、Stage4 レンダラーをリファクタしてコード重複なくソース切替を実装。仕様変更は関連 docs に反映。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo 更新、Plan 承認済み内容の通りに進行。
    - 想定影響ファイル: `src/pptx_generator/pipeline/template_extractor.py`, `cli_handlers/template_extraction.py`, `cli_commands/template.py`, `src/pptx_generator/models/*`, `pipeline/draft_structuring/static_runtime.py`, `pipeline/renderer/*`, テスト各種。
    - リスク: ソース種別伝搬漏れによる後段失敗、Stage4 リファクタ時のバグ混入、テンプレ構造差異による挙動変化。
    - テスト方針: `uv run --extra dev pytest tests/template_audit/test_template_extractor_jobspec_output.py`, 静的モード関連統合テスト、オプション切替用追加テスト。
    - ロールバック方法: TemplateExtractor/レンダラー変更を revert して従来レイアウトベースに戻す。
    - 承認メッセージ ID／リンク: （ユーザー承認済み）
- [x] 設計・実装方針の確定
  - メモ: Plan 承認内容を踏まえた設計・実装方針をここに記載し、ユーザー確認が必要な論点があれば列挙する。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: TemplateExtractor／CLI／モデルに `--from {slide,template}` と `template_source`/`prototype_index` を追加し、Stage2〜4 でメタを伝搬。SimpleRendererStep は `template_source=slide` 時にプロトタイプスライドを再利用してレンダリングし、余剰スライドを削除するよう調整済み。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/pipeline/render/test_renderer_rich_content.py`、`tests/template_audit/test_template_extractor_jobspec_output.py`、`tests/cli/test_cli_prepare_stage_flow.py`、`tests/integration/test_cli_generate_pipeline_flow.py::test_cli_template_emits_slide_snapshot` を実行し成功。
- [x] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 
