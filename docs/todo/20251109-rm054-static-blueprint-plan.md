---
目的: 静的テンプレート構成統合の計画と調査タスクを整理する
関連ブランチ: feat/rm054-static-blueprint-plan
関連Issue: #272
roadmap_item: RM-054 静的テンプレ構成統合
---

- [x] ブランチ作成と初期コミット
  - メモ: ブランチ `feat/rm054-static-blueprint-plan` を main から作成し、本 ToDo 追加の初期コミットを実施する
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan を記録（2025-11-09）
    - 対象整理（スコープ、対象ファイル、前提）: 静的テンプレ統合に向けて工程1〜3および CLI の仕様と実装を拡張し、Blueprint ベースの静的モードを追加する。動的モードとの後方互換性を維持しつつ、既存ドキュメント・サンプルを更新する。
    - ドキュメント／コード修正方針: 要件・設計ドキュメントの整合更新、新規 Blueprint 設計メモ追加。テンプレ抽出・工程2・工程3・CLI の実装を改修し、Blueprint モデルと静的モード処理を導入。サンプル・テストも静的モードに対応させる。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo と関連ドキュメントで進捗を共有し、PR に Plan 承認情報を記録。必要に応じて `docs/notes/` へ補足整理。
    - 想定影響ファイル: `docs/requirements/stages/stage-02-content-normalization.md`, `docs/requirements/stages/stage-03-mapping.md`, `docs/design/schema/stage-01-template-preparation.md`, `docs/design/cli-command-reference.md`, `docs/design/rm054-static-template-blueprint.md`（新規）, `docs/roadmap/roadmap.md`, `src/pptx_generator/models.py`, `src/pptx_generator/cli.py`, `src/pptx_generator/pipeline/*`, `samples/extract/*`, `tests/test_cli_integration.py` ほか関連テスト。
    - リスク: 静的/動的モード分岐による既存動作の破壊的影響、Blueprint と JobSpec の整合性欠如、CLI オプション互換性の破壊。ドキュメントと実装差異。
    - テスト方針: 既存テスト更新に加え、静的モードの統合テストと単体テストを追加。`uv run --extra dev pytest` で全体確認。
    - ロールバック方法: 変更済みドキュメント・コードを個別に `git revert` で戻し、`--mode` オプション必須化を解除して Blueprint 処理を元に戻す。
    - 承認メッセージ ID／リンク: ユーザー承認 (2025-11-09)
- [x] 設計・実装方針の確定
  - メモ: 静的モードでは Blueprint から slot 単位でカードを生成し、工程3で slot 充足検証と `generate_ready` 直接生成を行う方針を確定。CLI `prepare` に `--mode` / `--template-spec` を追加し、mapping は static 時にバイパス処理。
- [x] ドキュメント更新（要件・設計）
  - メモ: `docs/requirements/stages/stage-02-content-normalization.md` / `stage-03-mapping.md`、`docs/design/schema/stage-01-template-preparation.md`、`docs/design/cli-command-reference.md`、新規メモ `docs/design/rm054-static-template-blueprint.md` を更新。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `TemplateSpec` に Blueprint モデル追加、テンプレ抽出・工程2・工程3・CLI を静的モード対応。`MappingStep` の static パススルーやメタ拡張を実装済み。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_cli_prepare.py tests/test_cli_integration.py::test_static_mode_pipeline` を実行し、新旧テストが成功することを確認。
- [x] ドキュメント更新
  - メモ: ロードマップ状況を更新し、静的モード仕様をドキュメントへ反映。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
- 計画方針を確定次第、承認メッセージ ID とあわせて記録する
