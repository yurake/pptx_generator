---
目的: RM-095 PPTX edit を Web API から呼び出せるようにする（CLI と同等のジョブキュー実行）
関連ブランチ: feat/rm095-stage5-edit
関連Issue: 未作成
roadmap_item: RM-095 Stage5 PPTX 編集反映
---

- [x] ブランチ作成・初期コミット・push
  - メモ: 既存ブランチ feat/rm095-stage5-edit を流用。初期コミット済み。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: Plan 承認待ち。REST エンドポイント `/edit` 追加範囲、入力（pptxアップロード/参照パス、edits_json）、認証（Bearer/HMAC）、出力（artifacts: pptx_url）、ジョブキュー統合を整理。
- [ ] 設計・実装方針の確定
  - メモ: API 仕様（リクエスト/レスポンス/ステータス取得）、job builder、artifact登録、エラーハンドリング、既存 CLI とのコード共通化方針を記載。
  - [ ] 設計・実装方針メモの共有（必要に応じて docs/notes 等へのリンク）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [ ] 実装
  - メモ: `/edit` ルート追加、build_edit_job 追加、artifacts に pptx_url 登録、PPTX_OUTPUT_ROOT/<tx>/edit/<job_id>/ 配下に保存。認証と tx/job_id 付与は既存フレームを流用。
- [ ] テスト・検証
  - メモ: API 経由の end-to-end（リクエスト→202→ジョブ完了→artifact取得）とエラーパス（入力不足/認証失敗/LLM失敗）を追加。
- [ ] ドキュメント更新
  - メモ: README/API セクションに `/edit` を追記。変更不要の場合も理由を記載。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: Issue 未作成のため対応後に更新。
- [ ] チェックリスト整合確認
  - メモ: 子タスク完了後に整合チェック。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載。

## メモ
- 前提/制約: CLI では job_queue 経由で同期実行済み。API は既存ステージ (templates/prepare/compose/gen) と同じ認証/HMAC・ジョブ管理に倣う。
- 決定と理由: 未定（Plan 承認後に更新）
- リスク(UNCONFIRMED): LLM失敗時のレスポンス仕様、アップロード/パス混在入力の検証不足、アーティファクト登録漏れ、tx/job_id の衝突。
- Now/Next: Now=Plan策定待ち。Next=設計方針確定→実装着手。
- テスト実績/抜け: なし（これから実施）
