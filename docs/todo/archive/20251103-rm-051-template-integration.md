---
目的: 工程1/2の統合要件と影響範囲を整理し、CLI 仕様ドラフトと更新計画を整える
関連ブランチ: feat/rm-051-template-integration
関連Issue: #260
roadmap_item: RM-051 テンプレ工程統合集約
---

- [x] ブランチ作成と初期コミット
  - メモ: 2025-11-03 main から feat/rm-051-template-integration を作成し、ToDo 追加を初期コミットとする
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - スコープ: `uv run pptx template` コマンドを新設し、テンプレ工程の抽出・検証を一括化する。`--with-release` 指定時に `tpl-release` を連携実行し、それ以外は抽出＋検証のみを実行する。既存 `tpl-extract` / `layout-validate` / `tpl-release` はヘルパー化して `template` コマンドから再利用し、個別コマンドとしては設計資料にのみ残す。全ドキュメントを 4 工程（テンプレ工程→コンテンツ準備→マッピング→レンダリング）体系に更新し、README など利用者向け資料から個別コマンド説明を除外する。
    - ドキュメント／コード修正方針: CLI 実装は `src/pptx_generator/cli.py` を中心にヘルパー抽出と新コマンド追加を行い、エラーコードやログ出力は既存仕様を踏襲する。ドキュメントは README、`docs/design`、`docs/requirements/stages`、`docs/runbooks`、`docs/notes`、`docs/roadmap/roadmap.md` など工程番号を含む箇所を洗い出して更新し、テンプレ工程統合メモを `docs/notes/20251103-template-pipeline-integration.md` として記録する。影響一覧を整理しつつ、旧 stage-01/02 文書を統合した新 `stage-01-template-pipeline.md` を作成する。
    - 確認・共有方法: ToDo へ進捗を適宜追記し、Plan 承認メッセージ（ユーザー 2025-11-03 承認）を記録。作業完了後に README・設計資料のリンクを確認し、必要なら `docs/` 配下の README へも追記する。
    - 想定影響ファイル: `src/pptx_generator/cli.py`、`tests/test_cli_integration.py`、`tests/test_cli_cheatsheet_flow.py`、`README.md`、`docs/design/cli-command-reference.md`、`docs/design/design.md`、`docs/requirements/stages/*`、`docs/runbooks/*.md`、`docs/roadmap/roadmap.md`、`docs/notes/20251103-template-pipeline-integration.md`（新規）、`docs/todo/20251103-rm-051-template-integration.md`。
    - リスク: ヘルパー抽出時に既存コマンドの挙動が変化する可能性、ドキュメント更新漏れによる工程番号不整合、`--with-release` 実行時の処理時間増加。段階的にコミットし、CLI テストと全文検索で検知する。
    - テスト方針: `uv run --extra dev pytest tests/test_cli_integration.py` を通し、新規 `template` コマンドケースを追加。`tests/test_cli_cheatsheet_flow.py` の更新と合わせて回帰確認。必要に応じて `uv run pptx template samples/templates/templates.pptx --output .pptx/extract` を実行し成果物を目視確認する。
    - ロールバック方法: `template` コマンド追加とドキュメント更新を revert し、旧 5 工程表記と既存コマンド案内を復帰させる。ヘルパー抽出が影響した場合は該当コミットのみ戻して個別コマンドの挙動を保全する。
    - 承認メッセージ ID／リンク: user-20251103-plan-approval
- [x] 設計・実装方針の確定
  - メモ: `src/pptx_generator/cli.py` に `TemplateExtractionResult` などのヘルパーを導入し、`template` サブコマンドから抽出・検証・リリースメタ実行を統合する方針を採用。既存 `tpl-extract` / `layout-validate` / `tpl-release` はヘルパーを共有して互換性を維持する。ドキュメントは 4 工程構成へ更新する。
- [x] ドキュメント更新（要件・設計）
  - メモ: README / design / requirements を 4 工程へ再編し、ステージ別資料のリネーム・stub 化を実施。CLI リファレンスは `template` コマンド中心に改訂。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `src/pptx_generator/cli.py` に `template` サブコマンドを追加し、共通ヘルパーを導入。既存テストを更新して統合コマンドへ対応。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest` を実行し 162 件成功（21.33s）。
- [x] ドキュメント更新
  - メモ: ロードマップ・README・notes を含む 4 工程反映と統合メモ追加を完了。runbook 影響なし確認。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [x] PR 作成
  - メモ: PR #261 https://github.com/yurake/pptx_generator/pull/261（2025-11-03 完了）

## メモ
