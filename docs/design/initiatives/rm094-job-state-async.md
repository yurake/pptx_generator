# ジョブ状態モデル＋非同期化設計（RM-094）

## 目的
- 4 stage（template / prepare / compose / gen）を非同期ジョブとして扱い、状態を一元管理する。
- job_id / transaction_id を公式化し、状態問い合わせ・キャンセル・再実行を簡易にする。
- ローカル環境でも動作する軽量キューで最小実装し、破壊的に同期実行を廃止する。

## スコープ / 非スコープ
- 対象: 4 stage の enqueue / 実行 / 状態管理、ステータス問い合わせ/キャンセル CLI、pipeline_trace とジョブレコード出力。
- 非対象: 外部メッセージキュー、並列ワーカー、永続ストレージ越しの分散実行、署名付き URL 発行。

## 前提
- ID: job_id / transaction_id は UUID4 を採用（RM-091 整合）。
- 出力配置: RM-092 の `PPTX_OUTPUT_ROOT/<transaction_id>/<stage>/<job_id>/` を基本。tx 未指定時は `.pptx/<stage>` にフォールバック。
- 言語・I/F: CLI を正とし、同期実行経路は廃止する。

## コンポーネント
- job_queue: ファイルベースのキュー（`.pptx/queue/pending/*.json`）。ジョブ要求を JSON で格納。
- job_store: ジョブレコードを `.pptx/jobs/<transaction_id>/<job_id>.json` に保存（状態・入力参照・出力パス・エラー）。
- worker: `pptx worker run` で pending をポーリングし、1 ジョブずつ実行。実行前後に job_store と trace を更新。
- cli handlers: `pptx template/prepare/compose/gen` は enqueue のみ実施し job_id を返す。`pptx status` / `pptx cancel` は job_store を参照・更新。

## 状態モデル
```
pending -> running -> succeeded
                 └-> failed
pending --------> canceled
```
- 再実行は新しい job_id を発行（同一 transaction_id を引き継ぎ可）。
- cancel: pending のみ即キャンセル。running は開始前チェックで best effort 停止。
- 失敗時は error 詳細を記録し failed へ遷移。

## データ構造
- ジョブリクエスト（queue entry; JSON）
  - job_id, transaction_id, stage, args（CLI 引数変換後の設定一式）, enqueued_at
- ジョブレコード（job_store）
  - job_id, transaction_id, stage, status, enqueued_at, started_at, finished_at
  - workdir（出力ルート）、inputs（参照パス）、outputs（成果物パス）、logs（trace / rendering_log 等へのパス）
  - error（message / traceback など）
- trace: `pipeline_trace.json` に `job_id, transaction_id, stage, status, started_at, finished_at, error` を追加。

## CLI I/F と同期挙動（B 案）
- CLI は「キューに積むが自身でワーカーを起動し完了まで待つ」同期挙動とする。API/外部は従来どおり非同期（pending→worker→完了）。
- `pptx template|prepare|compose|gen ... [--transaction-id <tx>]`
  - 動作: enqueue → 即座に worker を 1 回起動し、該当 job が終了するまで待機。
  - 出力: `{job_id, transaction_id, status}`（完了時点のステータス）。エラー時はジョブレコードの error を拾って非 0 で終了。
- `pptx status --job-id <id> [--format json]`
  - job_store を読み取り status / outputs / error を表示。
- `pptx cancel --job-id <id>`
  - pending を canceled へ更新。running は開始前チェックで停止できる場合のみ反映。
- `pptx worker run [--once]`
  - バックグラウンド処理向け。pending を取得し running→終了まで処理。--once で 1 ジョブのみ実行。

## エラー/リトライ方針
- failed に error を記録。リトライは元の transaction_id を指定して新 job を enqueue。
- worker での例外は job_store と trace へ反映し、キューに戻さない（手動再 enqueue）。

## 移行と互換性
- CLI は同期完了を待つため、従来の UX を維持しつつ内部経路のみキュー化する。既存スクリプトの戻り値は成功/失敗を従来どおり exit code で判断可能。
- `.pptx/queue` と `.pptx/jobs` 生成を許容するよう CI/テストのクリーンアップを調整する。

## テスト計画（実装とセットで追加）
- 単体: job_queue（enqueue/dequeue/cancel）、job_store の状態更新、状態遷移バリデーション。
- 統合: template→prepare→compose→gen を enqueue → worker run → status 確認で succeeded を検証。失敗シナリオで failed を確認。
- trace: `pipeline_trace.json` に job_id/transaction_id/status が出力されることを検証。
