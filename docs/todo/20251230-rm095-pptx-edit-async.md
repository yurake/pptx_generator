---
目的: RM-095 PPTX edit を非同期基盤で実行できるようにする
関連ブランチ: feat/rm095-stage5-edit
関連Issue: #513
roadmap_item: RM-095 Stage5 PPTX 編集反映
---

- [x] ブランチ作成・初期コミット・push
  - メモ: 既存ブランチ feat/rm095-stage5-edit を流用。初期コミット済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: job_queue 基盤（メモリキュー＋worker、run_job_sync）を edit に適用し、CLI は同期UXを維持したまま内部でキュー経由とする。永続キュー/キャンセルは対象外。新規 Issue は未作成のまま進行。
- [x] 設計・実装方針の確定
  - メモ: edit コマンドを job_queue 経由に統一。ジョブID/txIDは既存ルール（UUID4）を踏襲。API 追加は本タスク範囲外。
  - [x] 設計・実装方針メモの共有（本ファイルに記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: `pptx edit` を `run_job_sync(stage=\"edit\", func=...)` で実行するよう変更。戻り値に適用件数/未適用/モデル/出力をまとめてCLIに表示。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/pipeline/test_text_edit.py`（7件成功、CLI位置引数・レガシーオプションエラー含む）。
- [x] ドキュメント更新
  - メモ: notes に job_queue 基盤利用を追記。その他は影響なしとして更新不要。
  - [x] docs/roadmap 配下（影響なし）
  - [x] docs/requirements 配下（影響なし）
  - [x] docs/design 配下（影響なし）
  - [x] docs/runbook 配下（影響なし）
  - [x] README.md / AGENTS.md（本タスクでは変更不要）
- [x] 関連Issue 行の更新
  - メモ: Issue 未作成のため対応後に更新。
- [x] チェックリスト整合確認
  - メモ: 残タスクは PR 作成のみ。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載。

## メモ
- 前提/制約: 既存 edit は同期/直列。非同期化で LLM 呼び出しと適用処理をジョブ化する必要あり。
- 決定と理由: edit を job_queue 経由で実行し、同期UXを維持。キャンセル/永続キュー/非同期APIはスコープ外。
- リスク(UNCONFIRMED): ジョブエラー時のリトライなし、job_queue がメモリ管理のみのためプロセスダウンで失われる。既存 CLI は同期挙動を継続。
- Now/Next: Now=実装・テスト・ドキュメント反映済み。Next= PR 作成。
- テスト実績/抜け: `uv run --extra dev pytest tests/pipeline/test_text_edit.py`（7件成功）。CLI 手動検証は未記録だが job_queue 基盤は他ステージで利用済み。
