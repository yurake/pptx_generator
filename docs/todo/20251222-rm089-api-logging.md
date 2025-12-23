---
目的: RM-089 API ログ強化（非同期ジョブの stdout / logs/out.log 出力整備）
関連ブランチ: feat/rm089-flask-web-api
関連Issue: 未作成
roadmap_item: RM-089 stage1-4 Flask Web/API 化
---

- [ ] ブランチ作成・初期コミット・push
  - メモ: 既存ブランチ feat/rm089-flask-web-api を継続利用。新規ブランチ作成なし。
    - 必ずmainからブランチを切る
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: Flask API の非同期ジョブ実行で、ジョブ処理開始/成功/失敗のログが stdout / logs/out.log に出ない問題を解消。API 応答仕様は変更しない。対象ファイルは `src/pptx_generator/api/flask_app.py` と必要に応じて `tests/api/test_flask_app.py`。
    - ドキュメント／コード修正方針: ロガー設定を流用しつつジョブ実行ラッパーに共通ログを追加（job_id/tx_id/stage・開始/成功/失敗・例外時の詳細）。ドリフトがあれば ToDo/notes に記録。
    - 確認・共有方法（レビュー、ToDo 更新など）: チャット承認後、本 ToDo を更新し、テスト結果をメモに記録。必要なら notes へ補足。
    - 想定影響ファイル: `src/pptx_generator/api/flask_app.py`, `tests/api/test_flask_app.py`（caplog 等を追加する場合）。
    - リスク: ログ量増大によるローテーション頻度増、スレッド間ログ混在。RotatingFileHandler と識別子付与で緩和予定。
    - テスト方針: `uv run --extra dev pytest tests/api/test_flask_app.py` を実行。必要に応じてログ出力確認のテストを追加。
    - ロールバック方法: ログ追加コミットを単独にし、問題時は当該コミットを revert する。
    - 承認メッセージ ID／リンク: チャット承認（本スレッド）
- [ ] 設計・実装方針の確定
  - メモ: Plan 承認内容を踏まえた設計・実装方針をここに記載し、ユーザー確認が必要な論点があれば列挙する。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [ ] 実装
  - メモ: 実装範囲や未対応事項があれば記載する
- [ ] テスト・検証
  - メモ: 実施したテスト内容と結果を記入する
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。

## 参照済みドキュメント
- docs/policies/context-engineering.md
- CONTRIBUTING.md
- docs/policies/task-management.md
- docs/todo/template.md
