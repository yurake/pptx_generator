---
目的: RM-095 Stage5 PPTX 編集反映 / /edit edits JSON 文字列パース対応
関連ブランチ: feat/rm095-edit-parse
関連Issue: #560
roadmap_item: RM-095 Stage5 PPTX 編集反映
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ名や初期コミット内容、push したコミットの内容、差分がない場合はその理由を記入する
    - 必ずmainからブランチを切る
    - 2026-01-26: feat/rm095-edit-parse を作成。初期コミット=bd1319e（ToDo追加）。push済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: /edit の multipart/form-data で edits が JSON 文字列として届く場合のパース対応。対象は src/pptx_generator/api/routes.py と tests/api/test_flask_app.py。空配列の扱いは現行挙動を維持。
    - ドキュメント／コード修正方針: _prepare_edit_payload で edits が str の場合に json.loads し、list 以外は 422。JSONDecodeError も 422。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo に進捗/結果を記録し PR 本文へテスト/UAT結果を記載。
    - 想定影響ファイル: routes.py（edits のパース）、test_flask_app.py（multipart edits の成功/失敗テスト）。
    - リスク: 無効 JSON の 422 が増える。空配列の扱いは現行仕様のまま。
    - テスト方針: `uv run --extra dev pytest tests/api/test_flask_app.py -k "test_edit_"`、`uv tool run diff-cover coverage.xml --compare-branch upstream/main`。
    - ロールバック方法: edits パースと追加テストを revert。
    - 承認メッセージ ID／リンク: 2026-01-26 ユーザー承認「OK」
- [x] 設計・実装方針の確定
  - メモ: _prepare_edit_payload で edits が str の場合に json.loads。list 以外は 422。JSONDecodeError も 422 とする。
  - [x] 設計・実装方針メモの共有（不要）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: edits が文字列の場合に JSON パースし、list 以外/不正 JSON は 422。
- [x] テスト・検証
  - メモ: 以下を簡潔に記載する
    - 自動テスト:
      - `uv run --extra dev pytest tests/api/test_flask_app.py -k "test_edit_"`
        - 結果: 14 passed
      - `uv tool run diff-cover coverage.xml --compare-branch upstream/main`
        - 結果: Diff coverage 100%
    - ユーザー経路の手動確認（必要な場合）:
      - `uv run flask --app pptx_generator.api.flask_app run --host 127.0.0.1 --port 8000`
      - `curl -X POST http://127.0.0.1:8000/edit -H "Authorization: Bearer $PPTX_API_BEARER_TOKEN" -F "file=@samples/templates/edit_sample.pptx" -F "edits=[{\"shape_id\": 1, \"contents\": \"Updated by uat\"}]" -F "transaction_id=tx-uat-edits-parse"`
      - `curl http://127.0.0.1:8000/jobs/<job_id> ...` で status=succeeded / pptx_url を確認
    - 生成物の確認があれば、その方法と結果: status の pptx_url を確認
- [x] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下（変更不要: 既存 RM-095 内の運用更新なし）
  - [x] docs/requirements 配下（変更不要: 要件変更なし）
  - [x] docs/design 配下（変更不要: 設計変更なし）
  - [x] docs/runbook 配下（変更不要: 運用手順変更なし）
  - [x] README.md / AGENTS.md（変更不要: 手順追加なし）
- [x] 関連Issue 行の更新
  - メモ: #560 を反映。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR #561 https://github.com/yurake/pptx_generator/pull/561

## メモ
- 連続性メモ（短文化し、更新があれば上書きする）※設計確定・実装完了・テスト完了・PR作成前後など状態変化のたびに更新
  - 前提/制約: /edit の edits が文字列で届くケースに限定して対応。
  - 決定と理由: JSON 文字列は list にパースし、list 以外/不正 JSON は 422。
  - リスク(UNCONFIRMED): edits の入力形式が曖昧な場合は 422 で落ちる。
  - Now/Next: PR作成済み。レビュー待ち。
  - テスト実績/抜け: pytest 14件パス、diff-cover 100%。
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
