---
目的: CLI オプションの名称を page-limit へ統一し、利用者向けヘルプを最新状態に整備する
関連ブランチ: feat/rm047-draft-structuring
関連Issue: 未作成
roadmap_item: RM-047 テンプレ統合構成生成AI連携
---

- [x] ブランチ作成と初期コミット
  - メモ: 既存ブランチ feat/rm047-draft-structuring を継続利用。初期コミットは過去対応で実施済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: `pptx prepare` サブコマンドの `--card-limit` オプションを `-p/--page-limit` に改名し、CLI 引数・オーケストレータ・テスト・ドキュメントの表記を統一する。ブランチは `feat/rm047-draft-structuring` を継続利用し、旧オプションは廃止する。
    - ドキュメント／コード修正方針: `src/pptx_generator/cli.py` と `src/pptx_generator/brief/orchestrator.py` で引数名称を変更し、関連テストと README / CLI リファレンスほか `--card-limit` 記載ドキュメントを更新する。
    - 確認・共有方法（レビュー、ToDo 更新など）: 作業後に ToDo を更新し、必要に応じてレビューで共有する。
    - 想定影響ファイル: `src/pptx_generator/cli.py`, `src/pptx_generator/brief/orchestrator.py`, `tests/test_cli_prepare.py`, `README.md`, `docs/design/cli-command-reference.md`, `docs/requirements/stages/stage-02-content-normalization.md` ほか `--card-limit` 記載箇所。
    - リスク: 旧オプション指定ジョブが実行時エラーとなる恐れ。名称変更時のテスト漏れや表記揺れによる混乱。
    - テスト方針: `uv run --extra dev pytest tests/test_cli_prepare.py` を実行し、オプション動作を確認する。
    - ロールバック方法: 変更コミットを `git revert` するか、作業ブランチで reset して再実施する。
    - 承認メッセージ ID／リンク: ユーザーメッセージ「ファイル名にrm047をつけて…」 (2025-11-09)
- [x] 設計・実装方針の確定
  - メモ: Plan 方針で確定。追加設計事項なし。
- [x] ドキュメント更新（要件・設計）
  - メモ: CLI オプション記述を `-p/--page-limit` へ更新。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `src/pptx_generator/cli.py`, `src/pptx_generator/brief/orchestrator.py`, `tests/test_cli_prepare.py` を `page_limit` 対応へ更新。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_cli_prepare.py`
- [x] ドキュメント更新
  - メモ: README, notes など CLI 説明を `-p/--page-limit` に統一。
  - [ ] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: Issue 未作成。必要に応じて更新する。
- [ ] PR 作成
  - メモ: PR 作成時に番号と URL を記録する。

## メモ
- RM-047 完了後の派生タスクとして CLI オプション整備を実施する。
