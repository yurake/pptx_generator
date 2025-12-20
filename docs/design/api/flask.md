# Flask API 設計メモ（RM-089 / RM-094 / RM-096 連動）

## 構成
- app factory（`create_app` 想定）で共通設定・ミドルウェアを注入。
- Blueprint 分割:
  - `/templates`, `/prepare`, `/compose`, `/gen`（ジョブ登録）
  - `/jobs/{job_id}`（状態取得）
  - `/transactions/{transaction_id}`（トランザクション一覧）
  - `/jobs/{job_id}/artifacts/{pptx|pdf}`（成果物取得、認証あり）

## ミドルウェア
- 認証: HMAC → Bearer の順に検証（auth.md 参照）。失敗で 401、権限不足は 403 予約。
- リクエストID: `X-Request-ID` をログへ。なければ生成。
- エラーハンドラ: 401/403/404/422/500 を JSON `{code,message,details?}` で返却。

## ジョブ実行
- RM-094 のキューラッパを利用（enqueue / run_job_sync）。`job_id`/`transaction_id` を払い出して PipelineContext に渡す。
- workdir 解決: RM-092 の `PPTX_OUTPUT_ROOT/<transaction_id>/<stage>/<job_id>/` 規約を利用。未設定は従来 `.pptx/<stage>` 互換。
- レスポンス: 202 で `job_id, transaction_id, status=pending, stage, status_url, transaction_url` を返却。

## 成果物取得
- エンドポイント: `/jobs/{job_id}/artifacts/pptx|pdf`。本体と同じ認証（HMAC/Bearer）。
- artifacts URL は固定パスを返す（署名付きURL導入時も同フィールド差し替えで対応）。

## 設定（例）
- 認証: `PPTX_API_HMAC_KEY_CURRENT`, `PPTX_API_HMAC_KEY_NEXT`, `PPTX_API_HMAC_CLOCK_SKEW_SEC`, `PPTX_API_HMAC_NONCE_TTL_SEC`, `PPTX_API_BEARER_TOKEN`
- 出力: `PPTX_OUTPUT_ROOT`（未設定時は `.pptx` 互換）
- ログ: `PPTX_API_LOG_LEVEL`（任意）、`X-Request-ID` ログ出力

## テスト方針
- ルート単体: auth 成否、202/404/401/403 のレスポンススキーマ、JobStatus のフィールド。
- スモーク: templates→prepare→compose→gen の happy path（最小モック実装でOK）。
- アーティファクト取得: `/jobs/{job_id}/artifacts/pptx` が認証付きで取得できること。
