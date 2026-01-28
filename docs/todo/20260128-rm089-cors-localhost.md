---
目的: RM-089 stage1-4 Flask Web/API 化 / CORS origin を環境変数で制御
関連ブランチ: fix/rm089-cors-localhost
関連Issue: 未作成
roadmap_item: RM-089 stage1-4 Flask Web/API 化
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ名や初期コミット内容、push したコミットの内容、差分がない場合はその理由を記入する
    - 必ずmainからブランチを切る
    - 2026-01-28: fix/rm089-cors-localhost を upstream/main から作成。初期コミット=c1d235c（ToDo追加）。push済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: CORS 許可オリジンを `PPTX_API_CORS_ORIGINS` で制御し、未設定時は `http://localhost` / `http://localhost:4200` を既定とする。対象は `src/pptx_generator/api/flask_app.py`、`tests/api/test_flask_app.py`、`docs/design/api/flask.md`。
    - ドキュメント／コード修正方針: Flask CORS 設定を環境変数ベースに変更し、テストと設計ドキュメントへ反映する。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo 更新 + PR 本文にテスト結果を記載する前提。
    - 想定影響ファイル: `src/pptx_generator/api/flask_app.py`、`tests/api/test_flask_app.py`、`docs/design/api/flask.md`。
    - リスク: 環境変数の未設定/誤設定で許可オリジンが不足する可能性。
    - テスト方針: `uv run --extra dev pytest tests/api/test_flask_app.py -k "cors"`、`uv tool run diff-cover coverage.xml --compare-branch upstream/main`。
    - ロールバック方法: CORS 設定変更とテスト/ドキュメント更新のコミットを revert。
    - 承認メッセージ ID／リンク: 2026-01-28 ユーザー承認「OK」
    - 参照済みドキュメント: `AGENTS.md`、`docs/policies/context-engineering.md`、`CONTRIBUTING.md`、`docs/policies/task-management.md`、`docs/todo/README.md`、`docs/design/api/flask.md`。
- [x] 設計・実装方針の確定
  - メモ: `PPTX_API_CORS_ORIGINS` のカンマ区切りで許可オリジンを設定し、未設定時は `http://localhost` / `http://localhost:4200` を既定とする。`*` 指定時は全許可とする。
  - [x] 設計・実装方針メモの共有（不要）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: Flask CORS 設定に環境変数読取を追加し、既定の許可オリジンと `*` 指定を実装。テスト更新と設計ドキュメント反映を実施。
- [x] テスト・検証
  - メモ: 以下を簡潔に記載する
    - 自動テスト:
      - `uv run --extra dev pytest tests/api/test_flask_app.py -k "cors"`
        - 結果: uv キャッシュ初期化失敗（/Users/keitokimura/.cache/uv の権限エラー）
      - `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/api/test_flask_app.py -k "cors"`
        - 結果: uv が panic（system-configuration の NULL object エラー）
      - `.venv/bin/python -m pytest tests/api/test_flask_app.py -k "cors"`
        - 結果: 2 passed（coverage.xml 出力）
      - `.venv/bin/python -m diff_cover.diff_cover_tool coverage.xml --compare-branch upstream/main`
        - 結果: diff_cover 未導入（ModuleNotFoundError）
    - ユーザー経路の手動確認（必要な場合）: 未実施（テストクライアントの OPTIONS で CORS ヘッダ確認）
    - 生成物の確認があれば、その方法と結果: coverage.xml を出力
- [x] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下（変更不要: RM-089 の更新なし）
  - [x] docs/requirements 配下（変更不要: 要件変更なし）
  - [x] docs/design 配下（変更反映: `docs/design/api/flask.md` の CORS 設定）
  - [x] docs/runbook 配下（変更不要: 運用手順の追加なし）
  - [x] README.md / AGENTS.md（変更不要: 手順追加なし）
- [ ] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 連続性メモ（短文化し、更新があれば上書きする）※設計確定・実装完了・テスト完了・PR作成前後など状態変化のたびに更新
  - 前提/制約: `PPTX_API_CORS_ORIGINS` で許可オリジンを制御し、未設定時は localhost 系を許可する。
  - 決定と理由: フロント/バックのポート差を吸収するため、CORS を環境変数化して運用で調整可能にする。
  - リスク(UNCONFIRMED): 設定ミスで許可オリジンが不足する可能性。
  - Now/Next: 実装とテスト完了。次は Issue 更新と PR 作成。
  - テスト実績/抜け: pytest 2件パス（.venv）。diff-cover 未実施（diff_cover 未導入 / uv 実行失敗）。
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
