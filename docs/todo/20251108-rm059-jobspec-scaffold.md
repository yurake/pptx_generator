---
目的: テンプレ抽出の jobspec スキャフォールドを工程3 JobSpec と整合させる方針と実装をまとめる
関連ブランチ: feat/rm057-jobspec-scaffold
関連Issue: 未作成
roadmap_item: RM-057 JobSpec スキャフォールド整合
---

- [x] ブランチ作成と初期コミット
  - メモ: 2025-11-08 feat/rm047-draft-structuring から feat/rm057-jobspec-scaffold を作成。初期コミットで本 ToDo を追加。
- [x] 計画策定（スコープ・前提の整理）
  - メモ:
    - 対象整理（スコープ、対象ファイル、前提）: テンプレ抽出で生成する `JobSpecScaffold` を工程3の `JobSpec` と互換化する。`src/pptx_generator/models.py`、`src/pptx_generator/pipeline/template_extractor.py`、`src/pptx_generator/cli.py`（compose フロー）、`samples/extract/jobspec.json` 等を想定。`docs/notes/20251105-jobspec-scaffold-validation.md` の調査結果を前提とし、既存 CLI 挙動は維持する。
    - ドキュメント／コード修正方針: `JobSpecScaffold`→`JobSpec` 変換ロジックを設計・実装し、CLI またはパイプラインへ組み込む。必要に応じて `samples/` と `docs/requirements/stages/stage-03-mapping.md` など関連ドキュメントを更新する。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo で進捗を更新し、Plan 承認内容をメモへ転記。
    - 想定影響ファイル: `src/pptx_generator/models.py`、`src/pptx_generator/pipeline/template_extractor.py`、`src/pptx_generator/cli.py`、`src/pptx_generator/__init__.py`（必要時）、`samples/extract/jobspec.json`、`docs/requirements/stages/stage-03-mapping.md`、関連ノートや README。
    - リスク: 他工程や外部ツールが現行スキャフォールド形式へ依存している場合の互換性低下、テンプレ情報だけでは `meta.title` / `auth` を補完しづらい点、`placeholders` 正規化時の情報損失。
    - テスト方針: 可能なら `uv run --extra dev pytest` で全体回帰。最低限 `tests/test_cli_integration.py` などで抽出→変換→compose の統合テストを追加／更新し、変換関数のユニットテストも検討。
    - ロールバック方法: 追加する変換モジュールと CLI・ドキュメントの変更を revert すれば従来のスキャフォールド挙動へ戻せる。
    - 承認メッセージ ID／リンク: ユーザー承認「okです、対応して」（2025-11-08）
- [x] 設計・実装方針の確定
  - メモ: JobSpecScaffold を CLI ローダーで吸収し、テンプレ抽出成果物を JobSpec へ整形する方針を採用。
- [x] ドキュメント更新（要件・設計）
  - メモ: `docs/requirements/stages/stage-03-mapping.md` へ自動変換仕様を追記。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `spec_loader.load_jobspec_from_path` を追加し、CLI `_load_jobspec` 経由で JobSpecScaffold→JobSpec 変換を適用。`tests/test_spec_loader.py` を新設。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_spec_loader.py`、`uv run pptx compose samples/extract/jobspec.json --template samples/templates/templates.pptx --brief-cards samples/prepare/prepare_card.json` を実行。
- [x] ドキュメント更新
  - メモ: `docs/roadmap/roadmap.md` で RM-057 ステータスを更新し、`docs/notes/20251105-jobspec-scaffold-validation.md` に実装内容を記録。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] docs/runbook 配下
  - メモ: 追加変更不要を確認。既存 Runbook で `.pptx/prepare` を参照しており今回の仕様変更影響なし。
- [x] README.md / AGENTS.md
  - メモ: 新規オプション追加がないため現状記述で問題なしと判断し確認完了。
- [x] 関連Issue 行の更新
  - メモ: 対応する Issue は存在しないため `関連Issue: 未作成` のまま確認済み。
- [x] PR 作成
  - メモ: PR #275 https://github.com/yurake/pptx_generator/pull/275（2025-11-08 完了）

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件を記載する。
