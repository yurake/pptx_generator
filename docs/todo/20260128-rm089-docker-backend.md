---
目的: RM-089 stage1-4 Flask Web/API 化 / 本番バックエンド用 Dockerfile 整備
関連ブランチ: chore/rm089-docker-backend
関連Issue: 未作成
roadmap_item: RM-089 stage1-4 Flask Web/API 化
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ名や初期コミット内容、push したコミットの内容、差分がない場合はその理由を記入する
    - 必ずmainからブランチを切る
    - 2026-01-28: chore/rm089-docker-backend を upstream/main から作成。初期コミット=d40eaa6（ToDo追加）。push済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: 本番バックエンド用 Dockerfile をリポジトリ直下に新規追加し、`.dockerignore` を修正する。`templates/` をコンテナに含める前提で運用する。
    - ドキュメント／コード修正方針: multi-stage build を採用し、`uv.lock` と整合する uv で依存をインストール。`gunicorn --factory` で Flask app を起動する。`.dockerignore` の混入テキストを修正する。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo 更新 + PR 本文に build/run/healthcheck 結果を記載する前提。
    - 想定影響ファイル: `Dockerfile`（新規）、`.dockerignore`（更新）、`docs/todo/20260128-rm089-docker-backend.md`。
    - リスク: system lib 不足で起動失敗、必須環境変数未設定で API 起動に失敗。
    - テスト方針: `docker build` / `docker run` / `curl http://localhost:8000/health`。
    - ロールバック方法: Dockerfile/.dockerignore を revert。
    - 承認メッセージ ID／リンク: 2026-01-28 ユーザー承認「OK」
    - 参照済みドキュメント: `AGENTS.md`、`docs/policies/context-engineering.md`、`CONTRIBUTING.md`、`docs/policies/task-management.md`、`docs/todo/README.md`。
- [ ] 設計・実装方針の確定
  - メモ: Plan 承認内容を踏まえた設計・実装方針をここに記載し、ユーザー確認が必要な論点があれば列挙する。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [ ] 実装
  - メモ: 実装範囲や未対応事項があれば記載する
- [ ] テスト・検証
  - メモ: 以下を簡潔に記載する
    - 自動テスト: 実行コマンドと結果（例: `uv run --extra dev pytest`, `diff-cover`）
    - ユーザー経路の手動確認（必要な場合）: 代表手順1本のコマンドと結果（例: docker build/run/curl, CLI compose→gen）
    - 生成物の確認があれば、その方法と結果
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
- 連続性メモ（短文化し、更新があれば上書きする）※設計確定・実装完了・テスト完了・PR作成前後など状態変化のたびに更新
  - 前提/制約: 
  - 決定と理由: 
  - リスク(UNCONFIRMED): 
  - Now/Next: 
  - テスト実績/抜け: 
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
