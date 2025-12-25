---
目的: RM-089 Web/API で templates/prepare のファイル添付入力に対応する
関連ブランチ: feat/rm089-flask-web-api
関連Issue: #455
roadmap_item: RM-089 stage1-4 Flask Web/API 化
---

- [x] ブランチ作成・初期コミット・push
  - メモ: 既存ブランチ feat/rm089-flask-web-api を継続利用（新規作成不要）
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan  
    - 対象整理（スコープ、対象ファイル、前提）: templates/prepare で multipart/form-data 添付を受け付け、従来のパス指定 JSON 互換を維持。PPTX_OUTPUT_ROOT 配下に tx 単位でアップロードを保存。OpenAPI を更新。  
    - ドキュメント／コード修正方針: Flask ハンドラで request.files を保存し、内部的に template_path / prepare_sources に差し替え。拡張子とサイズのバリデーションを追加。OpenAPI で multipart を追記し、説明に添付対応を明記。  
    - 確認・共有方法（レビュー、ToDo 更新など）: この ToDo へ進捗を記録し、API テスト結果を共有。  
    - 想定影響ファイル: src/pptx_generator/api/flask_app.py, docs/design/api/openapi.yaml, tests/api/test_flask_app.py（新規追加テスト）。  
    - リスク: 大容量アップロードによる OOM/ディスク枯渇、パスと添付の競合、OpenAPI との乖離。  
    - テスト方針: pytest で multipart 正常系/異常系（未指定、拡張子不正、併用時の優先順位）を追加。既存スモークが通ることを確認。  
    - ロールバック方法: 変更を専用コミットに分離し、問題時は該当コミットを revert。  
    - 承認メッセージ ID／リンク: なし（本メモで承認依頼）
- [x] 設計・実装方針の確定
  - メモ: templates は1ファイル前提。添付と path の両方指定は 422（優先なし）、両方未指定も 422。いずれか一方必須。prepare は複数可で添付＋path を併用可、両方未指定は 422。非同期投入前にバリデーションを行う。PPTX_OUTPUT_ROOT/<tx>/uploads/ へ保存し、secure_filename + UUID をアンダースコア連結で衝突回避。拡張子ホワイトリストと最大サイズ（デフォルト 500MB、413 応答）でガード。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: multipart 受理・保存・内部パス差し替え、拡張子/サイズ検証、OpenAPI 更新を実施済み。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/api/test_flask_app.py` で multipart 正常/異常および回帰を確認済み。
- [x] ドキュメント更新
  - メモ: OpenAPI を multipart 対応に更新済み。追加の設計メモ更新は不要と判断。roadmap/requirements/design/runbook/README/AGENTS は整合確認済みで変更不要。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: Issue 番号確定後に `関連Issue` を更新する
- [x] チェックリスト整合確認
  - メモ: PR 作成以外完了を確認。
- [x] PR 作成
  - メモ: PR #456 https://github.com/yurake/pptx_generator/pull/456（2025-12-25 完了）

## メモ
- 参照済み: docs/policies/context-engineering.md / CONTRIBUTING.md / docs/policies/task-management.md
