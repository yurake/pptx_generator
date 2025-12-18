---
目的: RM-094 ジョブ状態モデル＋非同期化（4 stage を非同期化しステータス管理を統合）
関連ブランチ: feat/rm094-job-state-async
関連Issue: #441
roadmap_item: RM-094 ジョブ状態モデル＋非同期化
---

- [x] ブランチ作成・初期コミット・push
  - メモ: main から feat/rm094-job-state-async を作成、Plan 記載コミット済み。origin へ push 済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan を転記済み（設計反映）。内容は下記のとおり。
    - 対象整理（スコープ、対象ファイル、前提）: 4 stage (template/prepare/compose/gen) をキュー経由で実行。job_id/transaction_id をキーに状態（pending/running/succeeded/failed）を扱い、CLI は同期完了待ち。出力配置は RM-092 規約。キャンセル/リトライ/永続ジョブ記録なし。
    - ドキュメント／コード修正方針: CLI ハンドラをキュー経由に変更。PipelineContext/trace へ job_id/transaction_id を伝搬。メモリキュー・ジョブ実行ラッパを新設。CLI 設計ガイドを更新。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo 更新とチャットで共有。設計メモを先にまとめて実装。
    - 想定影響ファイル: src/pptx_generator/pipeline/base.py, src/pptx_generator/cli_commands/*, 新規 runtime/job_queue.py, runtime/job_context.py, docs/design/cli/cli-command-reference.md など。
    - リスク: CLI 実行フロー変更、メモリキューによるクラッシュ時再開不可、ステータス/キャンセル未提供。
    - テスト方針: キュー単体の状態遷移、CLI 各ステージで run_job_sync 経由になることを確認するテスト追加。
    - ロールバック方法: キュー導入コミットを revert。
    - 承認メッセージ ID／リンク: ユーザー承認（本チャット 2025-12-18 指示: 1,2 実施・実装前に設計）。
    - 参照済みドキュメント: docs/policies/context-engineering.md, CONTRIBUTING.md, docs/policies/task-management.md, docs/roadmap/roadmap.md (RM-094), docs/notes/20251217-rm089-web-if.md
- [x] 設計・実装方針の確定
  - メモ: 非同期基盤/状態モデルの設計をまとめた。docs/design/initiatives/rm094-job-state-async.md に記載。CLI は内部キュー経由で同期完了待ち、API はキュー＋並列ワーカー（同一プロセス内）で非同期。キャンセル/自動リトライ/ジョブ記録ファイルは実装しない。
    - 状態モデル: pending → running → succeeded/failed。再実行は新 job_id を発行。キャンセル機能なし。
    - トレース/記録: pipeline_trace.json に `job_id`, `transaction_id`, `stage`, `status`, `started_at`, `finished_at`, `error` を追加。ジョブ記録ファイルは出力しない（必要ならクライアント側で保持）。
    - 出力配置: RM-092 に合わせ `PPTX_OUTPUT_ROOT/<transaction_id>/<stage>/<job_id>/`。CLI 互換の `.pptx/<stage>` は transaction_id 未指定時に fallback として維持。
    - キュー/ワーカー: メモリキュー。API 用は同一プロセス内で複数ワーカー並列可（スレッド/async）。CLI は enqueue 後に自前ワーカーで即実行し完了まで待つ（同期 UX）。
    - CLI インターフェース: `pptx template|prepare|compose|gen ...` はキュー経由で実行し完了まで待つ。`status`/`cancel` は実装しない。
    - エラー/リトライ: 自動リトライなし。失敗時は新しい job で再 enqueue。trace に error を記録。
    - 時刻/ID: job_id/transaction_id は UUID4 を標準。started_at/finished_at は ISO8601 UTC。
    - 互換性: CLI は完了まで待つ UX を維持しつつ内部はキュー化。status/cancel コマンドは提供しない。
  - [x] 設計・実装方針メモの共有（docs/design/initiatives/rm094-job-state-async.md）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: メモリキュー・ジョブコンテキストを追加し、PipelineContext へ job_id/tx_id を注入。CLI 各ステージ（template/prepare/compose/gen）を run_job_sync 経由に変更。CLI 設計ガイド更新。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/runtime/test_job_queue.py tests/cli/test_cli_job_queue_flow.py`
- [ ] ドキュメント更新
  - メモ: cli-command-reference.md 更新済み。roadmap を進行中に更新済み。requirements/runbook/README/AGENTS は未更新（必要に応じて別途）。
  - [x] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [ ] チェックリスト整合確認
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
