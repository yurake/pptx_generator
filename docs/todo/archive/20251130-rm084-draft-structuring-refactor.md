---
目的: RM-084 CLI/Pipeline リファクタビリティ向上 - `DraftStructuringStep` の責務分離とメソッド整理
関連ブランチ: chore/rm084-cli-refactorability
関連Issue: #351
roadmap_item: RM-084 CLI/Pipeline リファクタビリティ向上
---

- [x] ブランチ作成・初期コミット・push
  - メモ: chore/rm084-cli-refactorability を main から作成済み。mapping リファクタに続き本タスクでも利用する。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: `src/pptx_generator/pipeline/draft_structuring.py` の `DraftStructuringStep.run` および `_build_document` を中心に、入力整形・スライド処理・成果物出力の責務を分割する。静的モード `_run_static_mode` についてもカード割付と GenerateReady 書き出しのヘルパー化を検討する。既存 JSON 出力・例外ポリシーは維持。
    - ドキュメント／コード修正方針: ランタイムデータを `DraftAccumulator` で一元管理し、`_build_work_items`・`_process_work_item`・`_finalize_draft_document` などのヘルパーを追加。`docs/notes/rm084-refactorability-assessment.md` に設計メモを追記済み。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo と PR で設計方針とテスト結果を共有。必要に応じて差分ログを添付。
    - 想定影響ファイル: `src/pptx_generator/pipeline/draft_structuring.py`, `docs/notes/rm084-refactorability-assessment.md`, `docs/todo/20251130-rm084-draft-structuring-refactor.md`, `tests/pipeline/compose/test_draft_structuring_step.py`（および関連テスト）。
    - リスク: レイアウト推薦ログや AI 統計の整合性が崩れる可能性。GenerateReady 出力の差分による downstream 影響。
    - テスト方針: `uv run --extra dev pytest tests/pipeline/compose/test_draft_structuring_step.py` を中心に、必要なら compose/CLI 経由の統合テストも実行する。
    - ロールバック方法: `draft_structuring.py` の差分を revert すれば元の挙動へ戻せる。ドキュメント更新は同一コミットで巻き戻し可能。
    - 承認メッセージ ID／リンク: ユーザー返信「ok」（2025-11-30）。
- [x] 設計・実装方針の確定
  - メモ: `docs/notes/rm084-refactorability-assessment.md` に DraftStructuringStep リファクタ設計メモを追記。ワークアイテム／アキュムレータ導入と静的モード見直し案を整理済み。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
    - メモ: `docs/notes/rm084-refactorability-assessment.md` に DraftStructuring リファクタの構成・静的モード方針を反映済み（2025-11-30 時点で最新）。
- [x] 実装
  - メモ: `DraftStructuringStep.run` / `_build_document` をヘルパー分割し、`DraftWorkItem`・`DraftAccumulator`・`_finalize_draft_document` を追加。`_build_generate_ready_meta_payload` もセクション集計・統計ヘルパーへ分解し、既存出力と例外を維持。静的モードは `_resolve_static_template_spec_path`・`_validate_static_template_spec`・`_write_static_outputs` で責務分離。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/pipeline/compose/test_draft_structuring_step.py` と `uv run --extra dev pytest` を実行し、いずれも成功。
- [x] ドキュメント更新
  - メモ: 設計メモは `docs/notes/rm084-refactorability-assessment.md` を更新済み。他ドキュメントは影響なし。
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 2025-12-02 時点で未作成。`todo-sync` 実行後に発行される Issue 番号を反映する。
- [x] チェックリスト整合確認
  - メモ: 2025-11-30 確認時点で未完タスクは「PR 作成」のみ。その他の子タスクは親タスクと整合している。
- [x] PR 作成
  - メモ: PR #362 https://github.com/yurake/pptx_generator/pull/362（2025-12-02 完了）

## メモ
- CLI から `_load_prompt_overrides` を再エクスポートし、`tests/cli/test_cli_static_prompt_templates.py` の import 互換性を確保。
- 次フェーズでは `prepare_ai/orchestrator.py` `_build_cards_static` の章割当・LLM 呼び出し・結果検証を個別ヘルパーへ分割する ToDo を起票予定。チャプター割当生成→プロンプト構築→LLM 応答整形の 3 段構成を Plan に落とし込む。
- `layout_validation/suite.py` `_build_layout_records` はアンカー解析・ヒューリスティック評価・警告集計をデータクラス化するリファクタ ToDo を新設し、Slot 評価ループを小関数へ切り出す方針で整理する。
- `api/app.py` `create_app` の FastAPI ルートは cards/logs など機能別 router へ移し、依存取得と例外処理を shared util へ抽出する Plan を準備する。
