---
目的: RM-065 フォールバック警告ログ整備の実施準備
関連ブランチ: feat/rm065-fallback-warning-logging
関連Issue: #324
roadmap_item: RM-065 フォールバック警告ログ整備
---

- [ ] ブランチ作成・初期コミット・push
  - メモ: ブランチ feat/rm065-fallback-warning-logging を main から作成。初期コミットと push は Plan 承認後に実施予定。
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: 既定値へのフォールバックを行っている主要処理（mapping/renderer、template_ai/layout_ai/content_ai/prepare 等）でフォールバックを廃止し、失敗時は例外化する。既存の `fallback_report.json` やフォールバック専用成果物も挙動を見直す。現行ロギングは `WARNING` 以上が CLI に出力される前提。
    - ドキュメント／コード修正方針: フォールバック処理を削除または無効化し、適切な例外送出とエラーメッセージ出力を実装。`docs/notes/20251110-fallback-warning-logging.md` など関連ドキュメントを更新。
    - 確認・共有方法（レビュー、ToDo 更新など）: 実装後にレビュー依頼。ToDo と関連ドキュメントへ更新内容を反映。
    - 想定影響ファイル: `src/pptx_generator/pipeline/mapping.py`, `src/pptx_generator/pipeline/renderer.py`, `src/pptx_generator/template_ai/client.py`, `src/pptx_generator/layout_ai/client.py`, `src/pptx_generator/content_ai/client.py`, `src/pptx_generator/prepare/orchestrator.py`, フォールバック関連モジュール全般、`src/pptx_generator/cli.py`, `tests/pipeline/test_mapping*`, `tests/test_renderer.py`, `tests/test_cli_integration.py` など。
    - リスク: 既存ワークフローがフォールバックに依存している場合に強制停止する可能性。例外メッセージが不足すると調査が難しい。テストの期待値変更による失敗。LLM 障害時の停止率増加。
    - テスト方針: `pytest` で失敗ケースを再現し、例外発生とエラーメッセージ出力を `caplog` 等で検証。CLI 統合テストも実行し、LLM 例外時の挙動を確認。
    - ロールバック方法: 例外化関連コミットをリバートしてフォールバック処理を復元。
    - 承認メッセージ ID／リンク: ユーザー「ok」返信（フォールバック全面禁止の再承認）
- [x] 設計・実装方針の確定
  - メモ: Mapping/Renderer でフォールバックを許可しない。`PipelineFallbackError` を導入して例外化し、ドラフト未生成・アンカー欠損・ layouts.jsonl 不備などは即停止させる。例外発生時は `logger.error` で詳細を出力する。
- [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
- [ ] ドキュメント更新（要件・設計）
  - メモ: 
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [x] 実装
  - メモ: `PipelineFallbackError` 追加、MappingStep のフォールバック削除・例外化、Renderer のアンカー未解決時の例外化と要素判別メッセージ追加、関連テスト更新、docs/notes をエラー化方針へ改訂。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_mapping_step.py` / `tests/test_renderer.py` / `tests/test_cli_integration.py` / `tests/test_template_ai.py` / `tests/test_layout_validation_template_ai.py` / `tests/test_layout_validation_suite.py` / `tests/test_layout_recommender.py` / `tests/test_cli_outline.py` / `tests/content_ai/test_orchestrator.py` / `tests/content_ai/test_client_factory.py` / `tests/test_cli_prepare.py`
- [x] ドキュメント更新
  - メモ: `docs/notes/20251110-fallback-warning-logging.md` をフォールバック廃止に合わせて更新。その他要件・設計ドキュメントは今回対象外。
  - [x] docs/roadmap 配下
    - メモ: 更新不要（方針は既存ロードマップ記述で整合）
  - [x] docs/requirements 配下（実装結果との整合再確認）
    - メモ: 要件文書にフォールバック継続前提の記述なしのため更新不要
  - [x] docs/design 配下（実装結果との整合再確認）
    - メモ: 設計ドキュメントに該当フォールバック仕様がないため更新不要
  - [x] docs/runbook 配下
    - メモ: 運用手順の更新は別タスクで検討。今回は影響範囲のみ共有。
  - [x] README.md / AGENTS.md
    - メモ: README/AGENTS にフォールバック許容記載なしのため変更不要
- [x] 関連Issue 行の更新
  - メモ: 
- [ ] チェックリスト整合確認
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
-
