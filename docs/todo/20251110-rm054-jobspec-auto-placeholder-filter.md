---
目的: jobspec生成時に自動描画プレースホルダーを除外しレンダリング崩れを防ぐ
関連ブランチ: feat/rm054-static-blueprint-plan
関連Issue: #272
roadmap_item: RM-054 静的テンプレ構成統合
---

- [ ] ブランチ作成と初期コミット
  - メモ: 既存ブランチ `feat/rm054-static-blueprint-plan` を継続利用する（追加コミットで対応予定）
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan を転記（ユーザー承認: 2025-11-10 "ok"）
    - 対象整理（スコープ、対象ファイル、前提）: `src/pptx_generator/pipeline/template_extractor.py` の jobspec 雛形生成ロジックを改修し、PowerPoint 自動描画プレースホルダー（スライド番号／日付／フッター等）を除外。関連ユニットテスト `tests/test_template_extractor.py` と設計ドキュメント（ `docs/design/schema/stage-01-template-preparation.md` ほか必要箇所）を更新。Blueprint 生成への影響が無いことを確認する。
    - ドキュメント／コード修正方針: `placeholder_type` を用いたフィルタリング対象リストを定義し、該当アンカーを jobspec 出力から外す。Blueprint 側は従来通り slot 化するが、自動描画プレースホルダーは template_spec/layouts に残す。ドキュメントへ仕様追記。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo ファイルで進捗管理し、完了時にメモ更新。必要に応じてユーザーへ状況報告。
    - 想定影響ファイル: `src/pptx_generator/pipeline/template_extractor.py`, `tests/test_template_extractor.py`, `docs/design/schema/stage-01-template-preparation.md`（追加で必要な設計/要件ドキュメント）。
    - リスク: `placeholder_type` 未設定ケースへの対応漏れ、自動描画以外の図形を誤って除外するリスク、Blueprint との整合性崩れ。
    - テスト方針: `uv run --extra dev pytest tests/test_template_extractor.py` 必須。必要に応じて `uv run --extra dev pytest tests/test_cli_cheatsheet_flow.py` で抽出フローを再確認。
    - ロールバック方法: 変更ファイルを個別に `git revert` することで従来の jobspec 出力へ戻せる。ドキュメント追記も同様。
    - 承認メッセージ ID／リンク: ユーザー承認 (2025-11-10, メッセージ "ok")
- [ ] 設計・実装方針の確定
  - メモ: 
- [ ] ドキュメント更新（要件・設計）
  - メモ: 
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: 
- [ ] テスト・検証
  - メモ: 
- [ ] ドキュメント更新
  - メモ: 
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
