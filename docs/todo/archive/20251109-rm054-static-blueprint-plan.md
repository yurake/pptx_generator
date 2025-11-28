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
    - 対象整理（スコープ、対象ファイル、前提）: 静的テンプレ統合に向けて stage 1〜3および CLI の仕様と実装を拡張し、Blueprint ベースの静的モードを追加する。動的モードとの後方互換性を維持しつつ、既存ドキュメント・サンプルを更新する。
    - ドキュメント／コード修正方針: 要件・設計ドキュメントの整合更新、新規 Blueprint 設計メモ追加。テンプレ抽出・stage 2・stage 3・CLI の実装を改修し、Blueprint モデルと静的モード処理を導入。サンプル・テストも静的モードに対応させる。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo と関連ドキュメントで進捗を共有し、PR に Plan 承認情報を記録。必要に応じて `docs/notes/` へ補足整理。
    - 想定影響ファイル: `docs/requirements/stages/stage-02-prepare.md`, `docs/requirements/stages/stage-03-compose.md`, `docs/design/schema/stage-01-template-preparation.md`, `docs/design/cli/cli-command-reference.md`, `docs/design/initiatives/template-blueprint.md`（新規）, `docs/roadmap/roadmap.md`, `src/pptx_generator/models.py`, `src/pptx_generator/cli.py`, `src/pptx_generator/pipeline/*`, `samples/extract/*`, `tests/test_cli_integration.py` ほか関連テスト。
    - リスク: 静的/動的モード分岐による既存動作の破壊的影響、Blueprint と JobSpec の整合性欠如、CLI オプション互換性の破壊。ドキュメントと実装差異。
    - テスト方針: 既存テスト更新に加え、静的モードの統合テストと単体テストを追加。`uv run --extra dev pytest` で全体確認。
    - ロールバック方法: 変更済みドキュメント・コードを個別に `git revert` で戻し、`--mode` オプション必須化を解除して Blueprint 処理を元に戻す。
    - 承認メッセージ ID／リンク: ユーザー承認 (2025-11-09)
- [x] 設計・実装方針の確定
  - メモ: 静的モードでは Blueprint から slot 単位でカードを生成し、stage 3 で slot 充足検証と `generate_ready` 直接生成を行う方針を確定。CLI `prepare` の `--template-spec` は最終的に廃止し、`jobspec.meta.template_spec_path` を参照する形へ統一。
- [x] ドキュメント更新（要件・設計）
  - メモ: `docs/requirements/stages/stage-02-prepare.md` / `stage-03-compose.md`、`docs/design/schema/stage-01-template-preparation.md`、`docs/design/cli/cli-command-reference.md`、新規メモ `docs/design/initiatives/template-blueprint.md` を更新。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: jobspec.meta.template_spec_path を追加し、静的モードは jobspec を参照して Blueprint を取得。`--template-spec` を廃止し CLI とパイプラインを統一。動的モードの AI ログをバッチ化し、呼び出し回数を 1 件扱いに変更。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_cli_prepare.py tests/test_cli_cheatsheet_flow.py tests/test_cli_integration.py::test_static_mode_pipeline` を実行し、静的・動的双方のフローが成功することを確認。
- [x] ドキュメント更新
  - メモ: CLI ガイドと requirements/design スキーマの修正を確認済み。Roadmap・Runbook・README/AGENTS は現状記載で静的モード概要をカバーしており、追記不要と判断。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [x] PR 作成
  - メモ: PR #298 https://github.com/yurake/pptx_generator/pull/298（2025-11-22 完了）

## メモ
- 2025-11-21: stage 2 の prepare LLM プロンプトを dynamic/static で分離し、static モードは Blueprint slot 単位の軽量プロンプト（chapters 要素数 1 固定）を使用するように変更。dynamic は従来どおり 1 回の LLM 呼び出しで複数カードを生成する構成を維持しつつ、両モード間の条件分岐をプロンプトから排除してトークン削減を図った。
- 2025-11-21: dynamic モードで subtitle が `generate_ready` / PPTX に反映されない問題を修正。`ContentSlide` の subtitle を優先し、`elements.subtitle` が存在しない場合でも mapping で保持されるよう調整。ユニットテストを更新し、subtitle が generate_ready まで伝播することを確認。
- 2025-11-22: `_build_cards_static` をスライド単位プロンプト仕様に合わせて仕上げ、slot 応答欠損時でもカード生成・`fulfilled=False` 設定・slot 集計反映が行われるように調整。`docs/design/initiatives/template-blueprint.md` にも仕様追記済み。
- 2025-11-22: 静的モード向けに `test_prepare_static_slot_missing_response` を追加し、`uv run --extra dev pytest tests/test_cli_prepare.py::test_prepare_static_fallback_without_chapters tests/test_cli_prepare.py::test_prepare_static_slot_missing_response` / `uv run --extra dev pytest` を実行して全テスト 176 件の成功を確認。
- 2025-11-23: テンプレ抽出 CLI の Template AI オプションとスナップショット出力を整理後、`uv run --extra dev pytest` を実行して 187 件成功を確認。レイアウト AI タグ保持の追加ログも `tests/test_layout_recommender.py` でカバー済み。
