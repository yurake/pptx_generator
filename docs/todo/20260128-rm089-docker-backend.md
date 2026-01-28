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
- [x] 設計・実装方針の確定
  - メモ: repo 直下に Dockerfile を追加し、`.dockerignore` を整備。templates を含め、multi-stage build + `gunicorn --factory` で API 起動する。
  - [x] 設計・実装方針メモの共有（不要）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: Dockerfile と `.dockerignore` を追加。templates をコピー対象とし、`.dockerignore` の混入テキストを修正した。
- [x] テスト・検証
  - メモ: 以下を簡潔に記載する
    - 自動テスト: 未実施（Docker 未導入で `docker` コマンド不在）
    - ユーザー経路の手動確認（必要な場合）: `docker build` / `docker run` / `curl /health` は環境制約で未実施
    - 生成物の確認があれば、その方法と結果: なし
- [x] ドキュメント更新
  - メモ: Dockerfile/.dockerignore 追加のみ。ドキュメント変更は不要と判断。
  - [x] docs/roadmap 配下（変更不要: RM-089 の更新なし）
  - [x] docs/requirements 配下（変更不要: 要件変更なし）
  - [x] docs/design 配下（変更不要: 仕様変更なし）
  - [x] docs/runbook 配下（変更不要: 変更なし）
  - [x] README.md / AGENTS.md（変更不要: 手順追加なし）
- [ ] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 連続性メモ（短文化し、更新があれば上書きする）※設計確定・実装完了・テスト完了・PR作成前後など状態変化のたびに更新
  - 前提/制約: 本番バックエンド用 Dockerfile を main に入れて運用する前提。templates を同梱する。
  - 決定と理由: 再現性確保のため repo 直下に Dockerfile を追加し、CORS/認証は環境変数で制御する。
  - リスク(UNCONFIRMED): system lib 不足や環境変数未設定で起動失敗の可能性。
  - Now/Next: 実装完了。Issue 更新と PR 作成、Docker 環境での build/run 確認が次。
  - テスト実績/抜け: Docker 未導入のため build/run/healthcheck 未実施。
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
