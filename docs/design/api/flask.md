# Flask API 設計メモ（RM-089 / RM-094 / RM-096 連動）

## 構成
- app factory（`create_app` 想定）で共通設定・ミドルウェアを注入。
- Blueprint 分割:
  - `/templates`, `/prepare`, `/compose`, `/gen`, `/edit`（ジョブ登録）
  - `/jobs/{job_id}`（状態取得）
  - `/transactions/{transaction_id}`（トランザクション一覧）
  - `/jobs/{job_id}/artifacts/{pptx|pdf}`（成果物取得、認証あり）
- 既存 FastAPI は本実装で置き換え、後方互換なしで完全削除予定。

## バリデーション / 制限
- request body 上限（例: 10MB）を設定。超過時は 413。
- `prepare_sources` の許可形式を明記（例: md/txt/json のファイルパス、プレーン文字列）。URL 経由の取得は今回許可しない前提。
- payload スキーマは Pydantic/attrs 等でサーバ側検証し、422 で返す。
- templates 入力: 添付ファイル1つまたは path 文字列のどちらか一方必須。両方指定は 422、両方未指定も 422。
- prepare 入力: 添付ファイル複数可、path 文字列も複数可で併用可。どちらも無い場合は 422。
- ジョブ投入前に入力存在チェック（ステージ毎に必要ファイルの有無を確認）。存在しない場合は同期バリデーションで 422。

## ファイル添付入力（templates / prepare）
- 受け付け形式: multipart/form-data（`file` パートを想定）。JSON の path 指定は互換維持。
- 保存先: `PPTX_OUTPUT_ROOT/<transaction_id>/uploads/`。`secure_filename` + UUID で衝突回避し、サニタイズ後のパスを内部で利用。
- templates: 添付ファイルを `template_path` とみなし、path 指定と同時指定時は 422。どちらか一方があればそれを採用。
- prepare: 添付ファイルを `prepare_sources` に追加する。path 指定と合わせて複数扱い。両方無い場合は 422。
- バリデーション: 拡張子ホワイトリスト（pptx / md / txt / json など必要最小限）、`MAX_CONTENT_LENGTH` を超える場合は 413。保存前に存在チェックを行い、非同期キュー投入前に同期 422 を返す。
- ログ: 保存ファイル名・サイズ・tx/job を INFO で記録し、添付が無い場合も判別できるようにする。

## ミドルウェア
- 認証: HMAC → Bearer の順に検証（auth.md 参照）。失敗で 401、権限不足は 403 予約。
- リクエストID: `X-Request-ID` をログへ。なければ生成。
- エラーハンドラ: 401/403/404/422/500 を JSON `{code,message,details?}` で返却。

## ジョブ実行
- RM-094 のキューラッパを利用（enqueue / run_job_sync）。`job_id`/`transaction_id` を払い出して PipelineContext に渡す。
- workdir 解決: RM-092 の `PPTX_OUTPUT_ROOT/<transaction_id>/<stage>/<job_id>/` 規約を利用。**transaction_id をキーに前段成果物を解決するため、PPTX_OUTPUT_ROOT 設定を前提とする**。
- レスポンス: 202 で `job_id, transaction_id, status=pending, stage, status_url, transaction_url` を返却。
- enqueue タイムアウト値とワーカー側リトライ（RM-094 設計）を確認し、API 層では即 202 返却のみとする。

## 成果物取得
- エンドポイント: `/jobs/{job_id}/artifacts/pptx|pdf`。本体と同じ認証（HMAC/Bearer）。
- artifacts URL は固定パスを返す（署名付きURL導入時も同フィールド差し替えで対応）。
- Content-Type/Disposition: PPTX は `application/vnd.openxmlformats-officedocument.presentationml.presentation`、PDF は `application/pdf`。`Content-Disposition` は `attachment; filename="proposal-{job_id}.pptx"` の形で返却。
- ダウンロード: `/jobs/{job_id}/artifacts/{pptx|pdf}` で認証付きダウンロード。存在しない場合は 404。
- エラー: JSON 不正は 400、必須フィールド欠落は 422、ボディ超過は 413、認証は 401/403、成果物欠如/パス不正は 404。

## 設定（例）
- 認証: `PPTX_API_HMAC_KEY_CURRENT`, `PPTX_API_HMAC_KEY_NEXT`, `PPTX_API_HMAC_CLOCK_SKEW_SEC`, `PPTX_API_HMAC_NONCE_TTL_SEC`, `PPTX_API_BEARER_TOKEN`
- 出力: `PPTX_OUTPUT_ROOT`（tx→前段成果物解決のため設定を推奨）
- 本文・添付サイズ: `PPTX_API_MAX_BODY`（既定 500MB）を `MAX_CONTENT_LENGTH` に設定。超過時は 413。
- ログ: `LOG_LEVEL`（任意）、`X-Request-ID` ログ出力

## ログ / 監査
- リクエストログに `request_id, job_id?, transaction_id?, auth_scheme(hmac/bearer), path, status` を記録。
- 認証失敗時は理由（署名不一致/時刻ずれ/nonce再利用/トークン不正）をログに残し、レスポンスは抽象化した `code/message` のみ返却。
- エラーログは API 層で出す（enqueue 失敗含む）。ジョブ実行中の失敗はワーカー側（RM-094）で状態遷移とスタックをログに残す。
- 通知/アラートは今回は未設定（ログのみ）。通知先・閾値は後続で検討（TODO）。

## レート制限・再送
- 共有シークレットがある前提で厳格な rate limit は今回設けない。ただし将来導入を想定し、429 エラーハンドラを準備しておく。
- HMAC + nonce でリプレイ防止。再送許容は nonce TTL と時刻ウィンドウで制御。

## テスト方針
- ルート単体: auth 成否、202/404/401/403 のレスポンススキーマ、JobStatus のフィールド。
- スモーク: templates→prepare→compose→gen の happy path（最小モック実装でOK）。
- tx のみ指定で前段成果物を自動解決するフロー（パス未指定）。前段成果物が無い場合の 422、tx 不明の 404。
- アーティファクト取得: `/jobs/{job_id}/artifacts/pptx` が認証付きで取得できること。

## API バージョニング / 移行
- 初期リリースは `/` 直配下。将来 `/v1` を付与する場合はルーティングで prefix を一括切替できる構成にする。
- FastAPI 実装は本実装で置き換え、後方互換なしで削除する。移行後は Flask API を正とし、FastAPI ルートは廃止。

## CORS
- 開発環境: 任意オリジン許可。
- 本番: 許可リストのみ（デフォルト拒否）に切り替える。

## 入出力ディレクトリ規約（API）
- 出力: `PPTX_OUTPUT_ROOT/<transaction_id>/<stage>/<job_id>/` に成果物を配置する。未設定時は `.pptx/<stage>` を利用する実装もあるが、API 経路では tx/job 付きパスを前提とする。
- 入力: `PPTX_INPUT_ROOT/<transaction_id>/<job_id>/` にクライアントから受け取った入力（テンプレや prepare ソース）を保存する。未設定時は `.pptx/input`。
- CLI は従来どおり tx/job なしの `.pptx/<stage>` 出力を既定とするため、API と CLI の出力パスは異なる（tx/job を付与したい場合は API を利用する）。edit は CLI も `PPTX_OUTPUT_ROOT/<tx>/<stage>/<job_id>/` に揃え済み。

## ヘルスチェック
- `/health` を 200 で返却（簡易ヘルス）。メトリクスは今回は提供しない。

## 保持期間・クリーンアップ
- 保持期限は「未設定」。運用で定期的に `PPTX_OUTPUT_ROOT` を掃除する前提（自動削除は今回導入しない）。

## Idempotency / 再送
- 今回は idempotency 未対応。再送時も毎回新規 `job_id` を払い出す。
- Idempotency-Key ヘッダ対応は将来検討（TODO）。

## 成果物レジストリ（tx 起点のルックアップ方針）
- `PPTX_OUTPUT_ROOT/<transaction_id>/registry.json` に各 stage の最新 job_id と標準成果物パス（tx ルートからの相対パス）を記録する。
- ステージ完了時にレジストリを更新し、次ステージは transaction_id のみで前段成果物を解決する。リクエストから内部生成物パス指定は廃止する。
- ルックアップ失敗時のエラー: tx 不明は 404、前段成果物未登録/未完は 422。
- tx 内で複数ジョブがある場合は「最後に成功した job」を採用（必要なら将来 job_id 明示指定オプションを検討）。
