---
目的: RM-095 Stage5 PPTX 編集反映 / /edit ファイルアップロード対応
関連ブランチ: feat/rm095-edit-upload
関連Issue: 未作成
roadmap_item: RM-095 Stage5 PPTX 編集反映
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ名や初期コミット内容、push したコミットの内容、差分がない場合はその理由を記入する
    - 必ずmainからブランチを切る
    - 2026-01-26: feat/rm095-edit-upload を作成。初期コミット=6721ff5（ToDo追加）。push済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: /edit の PPTX アップロード対応のみ。対象は src/pptx_generator/api/routes.py と tests/api/test_flask_app.py。multipart + pptx_path 同時指定は 422 を維持。
    - ドキュメント／コード修正方針: edit の payload 準備時に uploads を許可し、1ファイルのみ保存して pptx_path に差し替え。_enqueue_job で tx_root を使って処理する。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo に進捗/結果を記録し PR にテスト結果を明記。
    - 想定影響ファイル: routes.py（_prepare_edit_payload / post_edit / _enqueue_job）、test_flask_app.py（/edit の multipart テスト追加）。
    - リスク: multipart 解析で edits が文字列のまま残る（次タスク対応）。大容量ファイルは MAX_CONTENT_LENGTH に依存。
    - テスト方針: `uv run --extra dev pytest tests/api/test_flask_app.py::test_edit_*`、`uv tool run diff-cover coverage.xml --compare-branch upstream/main`。
    - ロールバック方法: _prepare_edit_payload と edit の multipart テストを revert。
    - 承認メッセージ ID／リンク: 2026-01-26 ユーザー承認「OK」
- [x] 設計・実装方針の確定
  - メモ: _prepare_edit_payload に tx_root を渡し、upload 1ファイルのみ許容して pptx_path に反映。post_edit からは _prepare_edit_payload を外し、_enqueue_job の edit 分岐で実行する。ALLOWED_UPLOAD_EXT は edit 専用で `.pptx` のみ使用。
  - [x] 設計・実装方針メモの共有（不要）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: edit の upload を許可し、tx_root 配下へ保存して pptx_path に差し替え。edit 分岐で _prepare_edit_payload を実行するように変更。
- [x] テスト・検証
  - メモ: 以下を簡潔に記載する
    - 自動テスト:
      - `uv run --extra dev pytest tests/api/test_flask_app.py -k "test_edit_"`
        - 結果: 11 passed
      - `uv tool run diff-cover coverage.xml --compare-branch upstream/main`
        - 結果: Diff coverage 100%
    - ユーザー経路の手動確認（必要な場合）: 未実施（/edit は API テストで代替）
    - 生成物の確認があれば、その方法と結果: 生成物は API テストで確認
- [x] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下（変更不要: 既存 RM-095 内の運用更新なし）
  - [x] docs/requirements 配下（変更不要: 要件変更なし）
  - [x] docs/design 配下（変更不要: 設計変更なし）
  - [x] docs/runbook 配下（変更不要: 運用手順変更なし）
  - [x] README.md / AGENTS.md（変更不要: 手順追加なし）
- [ ] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 連続性メモ（短文化し、更新があれば上書きする）※設計確定・実装完了・テスト完了・PR作成前後など状態変化のたびに更新
  - 前提/制約: /edit のファイルアップロードのみ対応。edits の JSON 文字列パースは次タスク。
  - 決定と理由: upload は tx_root 配下に保存し pptx_path に差し替える。pptx_path と同時指定は 422 を維持。
  - リスク(UNCONFIRMED): multipart で edits が文字列のまま残る場合は 422 になる。
  - Now/Next: 実装・テスト完了。次は Issue/PR 作成。
  - テスト実績/抜け: pytest 11件パス、diff-cover 100%。
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
