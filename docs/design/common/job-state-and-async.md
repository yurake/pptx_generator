# ジョブ状態モデル＋非同期化（共通設計）

## 目的
- 4 stage（template / prepare / compose / gen）をジョブとして扱い、キュー＋ワーカー経由で統一的に実行する。
- `job_id` / `transaction_id` を公式化し、並列ワーカーでも重複実行せず結果を返せるようにする。
- CLI は同期 UX を維持しつつ内部はキュー経由、API は非同期＋並列ワーカーを許容する。

## 適用範囲
- 対象: 4 stage の enqueue / 実行 / 状態管理（メモリ管理）、`pipeline_trace` 出力。
- 非対象: 外部メッセージキュー、ジョブ状態の永続化、キャンセル、リトライ、署名付き URL 発行。
- インタフェース: CLI を正とし、API/外部クライアントは enqueue のみを受け付ける。

## 前提
- ID: `job_id` / `transaction_id` は UUID4 を採用（RM-091 整合）。
- 出力配置: RM-092 の `PPTX_OUTPUT_ROOT/<transaction_id>/<stage>/<job_id>/` を基本。tx 未指定時は `.pptx/<stage>` にフォールバック。
- ランタイム: メモリ内キュー＋ワーカーで完結する（永続キューなし）。同期 CLI はワーカー完了まで待機。

## コンポーネント
- job_queue: メモリキュー（FIFO）。揮発メモリのみで管理し、永続化しない。
- worker: 同一プロセス内で複数ワーカーを起動可能（スレッド/async）。キューからジョブを取り出し stage を実行し、`pipeline_trace` を出力。
- cli handlers: `pptx template/prepare/compose/gen` は enqueue の上で自前ワーカーを起動し完了まで待つ（同期 UX）。API からの enqueue は常駐ワーカーが非同期に処理。

## 状態モデル
```
pending -> running -> succeeded
                 └-> failed
pending --------> canceled
```
- 再実行は新しい `job_id` を発行（同一 `transaction_id` を引き継ぎ可）。
- cancel: pending のみ即キャンセル。running は開始前チェックで best effort 停止。
- 失敗時は error 詳細を記録し failed へ遷移。

## データ構造
- ジョブリクエスト（queue entry; JSON）
  - `job_id`, `transaction_id`, `stage`, `args`（CLI 引数変換後の設定一式）, `enqueued_at`
- ジョブレコード: 永続ファイルは残さない（必要時はクライアント側で保持）。実行中の状態はメモリ保持のみ。
- trace: `pipeline_trace.json` に `job_id, transaction_id, stage, status, started_at, finished_at, error` を追加（stage の output_dir 配下に従来どおり書き出し）。

## CLI / API 挙動
- CLI: キューに積んで自前ワーカーで即実行し完了まで待つ（同期）。`pptx status` / `cancel` は実装しない。
- API/外部: enqueue のみ。常駐ワーカー（同一プロセス内で複数並列可）が非同期に処理。
- レスポンス例:
  - 受け付け: `POST /{stage}` は 202/200 で `{job_id, transaction_id, status: "pending"}` を返却。
  - 取得: `GET /jobs/{job_id}` で `status`（pending/running/succeeded/failed）と成果物 URL/エラーを返す。ポーリング基本、オプションで `wait`/`callback_url` を許容。

## エラー / リトライ
- 自動リトライなし。失敗時はクライアントが新しい job を enqueue。
- worker での例外は `pipeline_trace` に error を記録し、キューに戻さない。

## 移行と互換性
- CLI は従来どおり完了まで待つが、内部でキュー/ワーカーを経由する。exit code で成功/失敗を判断可能。
- キュー/ジョブの永続ディレクトリは作らない（メモリ管理のみ）。ファイルクリーンアップは不要。
- API 層はキューラッパを利用し、enqueue 失敗時のみ API でエラーログを出す。
