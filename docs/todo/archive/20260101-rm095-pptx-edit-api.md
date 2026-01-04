---
目的: RM-095 PPTX edit を Web API から呼び出せるようにする（CLI と同等のジョブキュー実行）
関連ブランチ: feat/rm095-stage5-edit
関連Issue: #515
roadmap_item: RM-095 Stage5 PPTX 編集反映
---

- [x] ブランチ作成・初期コミット・push
  - メモ: 既存ブランチ feat/rm095-stage5-edit を流用。初期コミット済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: REST `/edit` を追加し、既存ステージと同じ認証 (Bearer/HMAC)・job_queue を利用。入力は PPTX（アップロードまたはパス）、任意で edits_json。LLM自動適用と手動適用の両方を許容。出力は `PPTX_OUTPUT_ROOT/<tx>/edit/<job_id>/` 配下の PPTX を artifacts.pptx_url で返す。
- [x] 設計・実装方針の確定
  - メモ: API 仕様（POST /edit）。入力: pptx パス（アップロード併用は不可で 422）、任意の edits_json（パス or JSON配列）、transaction_id（任意）、output（任意、未指定時 `PPTX_OUTPUT_ROOT/<tx>/edit/<job_id>/`）。認証: Bearer/HMAC。処理: job_queue enqueue stage=edit（CLIと同ロジック）。レスポンス: genと同じ 202 ボディ形式（job_id/tx/status/stage/status_url/transaction_url/timestamps/artifacts/error）。artifacts に pptx_url を登録。GET /jobs/<id> で状態確認、/jobs/<id>/artifacts/pptx で取得。エラー: 422 (入力), 401 (認証), ジョブ失敗時は error フィールド。
  - [x] 設計・実装方針メモの共有（ToDo本体に記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: `/edit` ルート追加、build_edit_job 追加、artifacts に pptx_url 登録、PPTX_OUTPUT_ROOT/<tx>/edit/<job_id>/ 配下に保存。認証と tx/job_id 付与は既存フレームを流用。アップロードとパスの排他チェックを追加。
- [x] テスト・検証
  - メモ: API 経由の E2E（POST→202→ジョブ完了→artifact取得）、エラー（入力不足/認証失敗/LLM失敗）を追加。pytest 全件実行済み。
- [x] ドキュメント更新
  - メモ: `/edit` を README/API/openapi に追記済み。変更不要箇所はなし。
  - [x] docs/roadmap 配下（影響なし）
  - [x] docs/requirements 配下（Stage5 追加で整合済み）
  - [x] docs/design 配下（Stage5 追加で整合済み）
  - [x] docs/runbook 配下（影響なしのため更新不要）
  - [x] README.md / AGENTS.md（README 更新済み、AGENTS 影響なし）
- [x] 関連Issue 行の更新
  - メモ: Issue 未作成のため対応後に更新。
- [x] チェックリスト整合確認
  - メモ: PR作成以外を完了済み。親子チェック整合 OK。
- [x] PR 作成
  - メモ: PR #525 https://github.com/yurake/pptx_generator/pull/525（2026-01-03 完了）

## メモ
- 前提/制約: CLI では job_queue 経由で同期実行済み。API は既存ステージ (templates/prepare/compose/gen) と同じ認証/HMAC・ジョブ管理に倣う。
- 決定と理由: 未定（Plan 承認後に更新）
- リスク(UNCONFIRMED): LLM失敗時のレスポンス仕様、アップロード/パス混在入力の検証不足、アーティファクト登録漏れ、tx/job_id の衝突。
- Now/Next: Now=Plan策定待ち。Next=設計方針確定→実装着手。
- テスト実績/抜け: なし（これから実施）
