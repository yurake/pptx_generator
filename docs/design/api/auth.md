# API 認証/認可設計メモ（RM-089/096 連動）

## スキーム
- **HMAC（サービス間/Bot 向け）**  
  - ヘッダ: `X-Signature`（HMAC-SHA256）、`X-Timestamp`（epoch秒）、任意で `X-Nonce`。  
  - 署名: `hex(hmac_sha256(secret, timestamp + "\n" + method + "\n" + path + "\n" + sha256(body)))`。  
  - 許容: 時刻ずれ ±300 秒、nonce 短期キャッシュでリプレイ防止。  
  - 鍵ローテ: current/next の2本を Key Vault/App Config で管理。検証時は両方試す。
- **Bearer（人手/curl/簡易クライアント向け）**  
  - 初期は固定トークン（Key Vault 管理）。将来 JWT/OIDC に差し替え可能な実装にする。  
  - OpenAPI の `BearerAuth` として OR で許可。
- **ダウンロードURL（RM-096 連動）**  
  - 現状は本体と同じ認証で `/jobs/{job_id}/artifacts/pptx|pdf` の固定パスを返し、そのまま GET。  
  - 将来署名付きURLに置き換える場合も同フィールドに署名付きURLを返すだけで契約維持。

## 運用・設定
- 秘密鍵: Key Vault/App Config 優先、環境変数はフォールバック。current/next でローテ。  
- パラメータ例: `PPTX_API_HMAC_KEY_CURRENT`, `PPTX_API_HMAC_KEY_NEXT`, `PPTX_API_HMAC_CLOCK_SKEW_SEC`, `PPTX_API_HMAC_NONCE_TTL_SEC`, `PPTX_API_BEARER_TOKEN`。  
- ネットワーク: VNet/Private Endpoint 前提。公開アクセスは無効化。  
- ログ/監査: 検証失敗理由（missing/expired/tampered）、使用スキーム（hmac/bearer）、リクエストID/tx/job を記録。

## エラー方針
- 401: 認証情報欠如/無効（HMAC/Bearer いずれも失敗）  
- 403: 権限なし（将来拡張用）  
- レスポンス: `{code, message, details?}` を返却し、ログには詳細（署名不一致/時刻ずれ/nonce再利用）を残す。

## 実装メモ（Flask 想定）
- ミドルウェアで HMAC → Bearer の順に検証。両方失敗で 401。  
- HMAC: timestamp チェック、nonce キャッシュ、2本鍵検証。  
- Bearer: 固定トークン検証。後で JWT バリデータに差し替え可能な形にしておく。

## OpenAPI との対応
- securitySchemes: `HmacAuth`（apiKey in header, X-Signature）、`BearerAuth`（http bearer）。  
- security: `[ { HmacAuth: [] }, { BearerAuth: [] } ]` で OR。  
- ダウンロードURL: `artifacts.*_url` は固定パスまたは署名付きURLを返すことを description に明記。

## 将来拡張
- JWT/OIDC 化（Bearer を差し替え）  
- 署名付きURL（RM-096 完了時に artifacts フィールドへ入れ替え）  
- mTLS は初期スコープ外。
