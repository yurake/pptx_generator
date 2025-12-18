---
目的: RM-094 ジョブ状態モデル＋非同期化（4 stage を非同期化しステータス管理を統合）
関連ブランチ: feat/rm094-job-state-async
関連Issue: #441
roadmap_item: RM-094 ジョブ状態モデル＋非同期化
---

- [ ] ブランチ作成・初期コミット・push
  - メモ: main から feat/rm094-job-state-async を作成済み。初期コミット・push は未実施。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan を転記。
    - 対象整理（スコープ、対象ファイル、前提）: 4 stage (template/prepare/compose/gen) を非同期化し同期経路を廃止。job_id/transaction_id をキーに状態（pending/running/succeeded/failed/canceled）を管理するローカルキュー/ジョブストアを追加。ステータス問い合わせ CLI/API 最小形。出力配置は RM-092 規約に合わせ tx/job 階層を基本とする。破壊的変更を許容。
    - ドキュメント／コード修正方針: CLI ハンドラを非同期投入に統一し同期実行削除。PipelineContext/trace へ状態と tx/job を記録。ローカルキュー実装・ステータス問い合わせハンドラを新設。README/CLI リファレンスで非同期化を反映。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo 更新とチャットで共有。設計メモを先にまとめてレビュー前提に実装着手。
    - 想定影響ファイル: src/pptx_generator/pipeline/base.py, src/pptx_generator/pipeline/trace.py, src/pptx_generator/cli_handlers/*, 新規 runtime/job_queue.py・job_store.py（仮）、ドキュメント（README.md / cli-command-reference）。
    - リスク: 同期 CLI 互換性の消失、パス/状態記録漏れによるトレース不整合、ローカルキューの耐久性は最小でクラッシュリカバリ非対応。
    - テスト方針: job_queue/store の単体（状態遷移・キャンセル/失敗）、非同期 template→prepare→compose→gen の最小統合テスト（pending→running→succeeded）、失敗系で failed 確認、pipeline_trace キー/状態の検証。
    - ロールバック方法: 非同期化一式を専用コミットにまとめ、問題時はそのコミットを revert。
    - 承認メッセージ ID／リンク: ユーザー承認（本チャット 2025-12-18 指示: 1,2 実施・実装前に設計）。
    - 参照済みドキュメント: docs/policies/context-engineering.md, CONTRIBUTING.md, docs/policies/task-management.md, docs/roadmap/roadmap.md (RM-094), docs/notes/20251217-rm089-web-if.md
- [x] 設計・実装方針の確定
  - メモ: 非同期基盤/状態モデルの設計をまとめた。docs/design/initiatives/rm094-job-state-async.md に記載。CLI/API でのステータス問い合わせ/キャンセル可否、キューの実体（ファイルベース）、ワーカー起動モデル、トレース出力のキー構成を定義。
    - 状態モデル: pending → running → succeeded/failed/canceled。再実行は新 job_id を発行。キャンセルは pending/準備中のみ受け付け、running は best effort（ジョブ実行開始前チェック）。
    - トレース/記録: pipeline_trace.json に `job_id`, `transaction_id`, `stage`, `status`, `started_at`, `finished_at`, `error` を追加。job レコード JSON を `.pptx/jobs/<tx>/<job_id>.json` に保持（状態・入力・出力パス・エラー・ログパス）。
    - 出力配置: RM-092 に合わせ `PPTX_OUTPUT_ROOT/<transaction_id>/<stage>/<job_id>/`。CLI 互換の `.pptx/<stage>` は transaction_id 未指定時に fallback として維持。
    - キュー/ワーカー: ローカルファイルベースのシンプルキュー（例: `.pptx/queue/pending/*.json`）。`pptx worker run` でポーリングし、1 ジョブずつ処理。並列化は本対応では行わずシリアル。キューは in-memory 併用だが、ジョブはファイル化してクラッシュ後も再開可能とする。
    - CLI インターフェース:
      - `pptx template|prepare|compose|gen [既存引数] --transaction-id <tx?>` → enqueue のみ。即時で `{job_id, transaction_id, status=pending, status_url_hint}` を出力。同期実行経路は廃止。
      - `pptx status --job-id <id>`: 状態・出力パス・エラーを表示。必要に応じて `--transaction-id` 併記可。
      - `pptx cancel --job-id <id>`: pending のみキャンセル。running は開始前チェックで停止し failed/canceled を記録。
      - `pptx worker run [--once]`: キューを消化。既存 stage 実行関数を呼び出し、ジョブレコードと trace を更新。
    - エラー/リトライ: 失敗時は status=failed と error 詳細を job レコード/trace に記録。リトライは新しい job として再 enqueue（同じ tx を引き継ぐ）。
    - 時刻/ID: job_id/transaction_id は UUID4 を標準。started_at/finished_at は ISO8601 UTC。
    - 互換性: 同期実行は廃止。CLI ドキュメントに非同期化を明記し、既存スクリプトは対応が必要になる旨を記載。
  - [x] 設計・実装方針メモの共有（docs/design/initiatives/rm094-job-state-async.md）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [ ] 実装
  - メモ: （着手前に設計メモ確定）
- [ ] テスト・検証
  - メモ: 
- [ ] ドキュメント更新
  - メモ: 
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [ ] チェックリスト整合確認
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
