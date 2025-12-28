---
目的: RM-096 成果物ダウンロードAPI分離の設計・実装と周辺ドキュメント更新
関連ブランチ: feat/rm096-download-api
関連Issue: #472
roadmap_item: RM-096 成果物ダウンロードAPI分離
---

- [x] ブランチ作成・初期コミット・push
  - メモ: main から feat/rm096-download-api を作成し、ToDo 追加コミット `docs(todo): add RM-096 download API task` を作成して push（push 時に config lock 警告はあったが反映済み）
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ:
    - 対象整理（スコープ、対象ファイル、前提）: RM-096 ダウンロードAPIの挙動整備。`src/pptx_generator/api/routes.py` を中心に artifacts フィールドとダウンロード解決を調整。既存 Flask API/HMAC・Bearer 認証前提。
    - ドキュメント／コード修正方針: gen 成果物の artifacts を API パスに統一し、ダウンロード時は registry と実ファイルを安全に解決。必要に応じて設計メモ更新。
    - 確認・共有方法（レビュー、ToDo 更新など）: この ToDo を更新し、実装・テスト結果を記載。コードレビューで共有。
    - 想定影響ファイル: `src/pptx_generator/api/routes.py`, `tests/api/test_flask_app.py`, 必要なら `docs/design/api/flask.md`.
    - リスク: artifacts のパス形式変更によるクライアント影響、registry 未更新時の解決漏れ、job_id→tx 解決の探索負荷。
    - テスト方針: API ルートのダウンロードと artifacts 表示を pytest で確認（gen 後のダウンロード成功・不在時 404・URL 返却）。
    - ロールバック方法: 当該変更コミットを revert する。
    - 承認メッセージ ID／リンク: ユーザー “ok” の返信で承認
- [x] 設計・実装方針の確定
  - メモ: gen 成果物の artifacts は API パスで返却し、ダウンロードは registry と実ファイルを安全に解決する方針で進行。registry から job_id を照会し、tx 直下の成果物のみ配布する。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: `src/pptx_generator/api/routes.py` で artifacts を API パス返却に変更し、ダウンロード時に registry/queue から安全にパス解決する処理を追加。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/api/test_flask_app.py::test_gen_artifacts_response_uses_api_url tests/api/test_flask_app.py::test_download_uses_registry_when_queue_missing` 実行、2件成功。
- [x] ドキュメント更新
  - メモ: 変更不要。設計メモは artifacts を固定 API パスで返す前提が既に記載済みで整合しているため追加なし。
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [x] チェックリスト整合確認
  - メモ: 予定タスクは PR 作成以外完了。PR 作成は未着手のため未チェック。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 連続性メモ（短文化し、更新があれば上書きする。別ファイルは作らない）
  - 前提/制約: 
  - 決定と理由: 
  - リスク(UNCONFIRMED): 
  - Now/Next: 
  - テスト実績/抜け: 
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
