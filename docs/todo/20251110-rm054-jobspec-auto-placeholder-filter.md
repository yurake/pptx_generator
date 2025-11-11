---
目的: jobspec生成時に自動描画プレースホルダーを除外しレンダリング崩れを防ぐ
関連ブランチ: feat/rm054-static-blueprint-plan
関連Issue: #272
roadmap_item: RM-054 静的テンプレ構成統合
---

- [x] ブランチ作成と初期コミット
  - メモ: 既存ブランチ `feat/rm054-static-blueprint-plan` を継続利用し、計画用コミットを追加済み
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan を転記（ユーザー承認: 2025-11-10 "ok"）
    - 対象整理（スコープ、対象ファイル、前提）: `src/pptx_generator/pipeline/template_extractor.py` の jobspec 雛形生成ロジックを改修し、自動描画プレースホルダーに `auto_draw` フラグを付与して保持。関連ユニットテスト `tests/test_template_extractor.py`／`tests/test_spec_loader.py` 等と設計ドキュメント（ `docs/design/schema/stage-01-template-preparation.md` ほか必要箇所）を更新し、Blueprint からは自動描画 slot を生成しない方針へ変更する。
    - ドキュメント／コード修正方針: `placeholder_type` を用いたフラグ判定を導入し、jobspec には `auto_draw=true` として残す一方 Blueprint では除外。レンダラー等で `auto_draw` を参照しテンプレ既定の描画枠を維持する。仕様追記で運用差分を明示する。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo ファイルで進捗管理し、完了時にメモ更新。必要に応じてユーザーへ状況報告。
    - 想定影響ファイル: `src/pptx_generator/pipeline/template_extractor.py`, `tests/test_template_extractor.py`, `docs/design/schema/stage-01-template-preparation.md`（追加で必要な設計/要件ドキュメント）。
    - リスク: `placeholder_type` 未設定ケースへの対応漏れ、自動描画以外の図形を誤って除外するリスク、Blueprint との整合性崩れ。
    - テスト方針: `uv run --extra dev pytest tests/test_template_extractor.py` 必須。必要に応じて `uv run --extra dev pytest tests/test_cli_cheatsheet_flow.py` で抽出フローを再確認。
    - ロールバック方法: 変更ファイルを個別に `git revert` することで従来の jobspec 出力へ戻せる。ドキュメント追記も同様。
    - 承認メッセージ ID／リンク: ユーザー承認 (2025-11-10, メッセージ "ok")
- [x] 設計・実装方針の確定
  - メモ: jobspec へ `auto_draw` 付与＋Blueprint から除外する設計を採用、レンダラー側でフラグを解釈する前提に調整
- [x] ドキュメント更新（要件・設計）
  - メモ: 要件面はテンプレ抽出仕様 (`docs/requirements/stages/stage-01-template-pipeline.md`) と整合していることを確認し、追加更新不要と判断。設計ドキュメントは `auto_draw` 追記済み。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: TemplateExtractor と SpecLoader を改修し、Blueprint/JobSpec 両方で `auto_draw` を処理。renderer 対応は未着手のため別工程で管理する。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_template_extractor.py tests/test_spec_loader.py` を実施し、新挙動を確認
- [x] ドキュメント更新
  - メモ: Roadmap・Runbook・README・AGENTS を確認し、`auto_draw` 追加後も整合しているため追記不要と判断。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
