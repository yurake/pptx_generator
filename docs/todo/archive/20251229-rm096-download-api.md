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
- [x] PR 作成
  - メモ: PR #474 https://github.com/yurake/pptx_generator/pull/474（2025-12-28 完了）

## メモ
- 連続性メモ（短文化し、更新があれば上書きする。別ファイルは作らない）
  - 前提/制約: PPTX_OUTPUT_ROOT 配下で tx/job に紐づく成果物のみ配布。認証は Bearer/HMAC 維持。
  - 決定と理由: gen artifacts は API パスで返却し、ダウンロード時は queue/registry から安全に解決（ディレクトリ逸脱防止）— RM-096 方針。
  - リスク(UNCONFIRMED): registry 未更新時の解決漏れの可能性（現状 SUCCEEDED 時に更新、scan フォールバックあり）。
  - Now/Next: PR 作成待ち。レビュー依頼前に todo-auto-complete 連動を確認。
  - テスト実績/抜け: pytest で artifacts API パス返却と registry フォールバックを確認（2件）。総合 API フロー再実行は未実施。
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
