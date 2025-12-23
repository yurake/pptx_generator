---
目的: RM-089 Web/API で templates/prepare のファイル添付入力に対応する
関連ブランチ: feat/rm089-flask-web-api
関連Issue: #455
roadmap_item: RM-089 stage1-4 Flask Web/API 化
---

- [ ] ブランチ作成・初期コミット・push
  - メモ: 既存ブランチ feat/rm089-flask-web-api を継続利用
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: 承認待ち Plan  
    - 対象整理（スコープ、対象ファイル、前提）: templates/prepare で multipart/form-data 添付を受け付け、従来のパス指定 JSON 互換を維持。PPTX_OUTPUT_ROOT 配下に tx 単位でアップロードを保存。OpenAPI を更新。  
    - ドキュメント／コード修正方針: Flask ハンドラで request.files を保存し、内部的に template_path / prepare_sources に差し替え。拡張子とサイズのバリデーションを追加。OpenAPI で multipart を追記し、説明に添付対応を明記。  
    - 確認・共有方法（レビュー、ToDo 更新など）: この ToDo へ進捗を記録し、API テスト結果を共有。  
    - 想定影響ファイル: src/pptx_generator/api/flask_app.py, docs/design/api/openapi.yaml, tests/api/test_flask_app.py（新規追加テスト）。  
    - リスク: 大容量アップロードによる OOM/ディスク枯渇、パスと添付の競合、OpenAPI との乖離。  
    - テスト方針: pytest で multipart 正常系/異常系（未指定、拡張子不正、併用時の優先順位）を追加。既存スモークが通ることを確認。  
    - ロールバック方法: 変更を専用コミットに分離し、問題時は該当コミットを revert。  
    - 承認メッセージ ID／リンク: なし（本メモで承認依頼）
- [ ] 設計・実装方針の確定
  - メモ: templates は1ファイル前提。添付と path の両方指定は 422（優先なし）、両方未指定も 422。いずれか一方必須。prepare は複数可で添付＋path を併用可、両方未指定は 422。非同期投入前にバリデーションを行う。PPTX_OUTPUT_ROOT/<tx>/uploads/ へ保存し、secure_filename + UUID で衝突回避。拡張子ホワイトリストと最大サイズでガード。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [ ] 実装
  - メモ: multipart 受理・保存・内部パス差し替えの追加、バリデーション、ログ追加、OpenAPI 更新を行う
- [ ] テスト・検証
  - メモ: pytest で multipart 正常系/異常系と既存スモークの回帰を実行
- [ ] ドキュメント更新
  - メモ: OpenAPI を更新。必要に応じて設計メモへの追記を検討。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: Issue 番号確定後に `関連Issue` を更新する
- [ ] チェックリスト整合確認
  - メモ: 親子タスクの完了状況を再確認する
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 参照済み: docs/policies/context-engineering.md / CONTRIBUTING.md / docs/policies/task-management.md
