---
目的: mainの stage 3 大型変更をfeat/rm-051-template-integrationへ取り込む
関連ブランチ: feat/rm-051-template-integration
関連Issue: #265
roadmap_item: RM-051 テンプレ stage 統合集約
---

- [x] ブランチ作成と初期コミット
  - メモ: mainから作成済みのfeat/rm-051-template-integrationを継続利用。初期コミットは2025-11-03のToDo追加。
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: `feat/rm-051-template-integration` に origin/main の stage 3（プレペア統合）変更を取り込み、CLI・パイプライン・tests・docs を最新化する。stage 1 統合実装との整合を維持する。origin/main を最新取得済み。`gh issue list` は TLS エラーで確認不可。
    - ドキュメント／コード修正方針: まず `git merge origin/main` で Stage3 プレペア機能の差分を取り込み、`src/pptx_generator/cli.py` を中心に競合を解消する。`src/pptx_generator/prepare/*` と `pipeline/prepare_normalization.py` の追加を正しく統合し、テストや README・requirements/design/notes 等の stage 表記も反映させる。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo へ進捗を逐次記録し、Plan 承認メッセージ ID を記録。作業完了時に README と docs 更新内容を自己チェックし、必要に応じて user へ共有する。
    - 想定影響ファイル: `src/pptx_generator/cli.py`、`src/pptx_generator/prepare/**/*`、`src/pptx_generator/pipeline/prepare_normalization.py`、`tests/test_cli_integration.py`、`tests/test_cli_content.py`、`tests/test_cli_outline.py`、`tests/test_mapping_step.py`、`README.md`、`docs/requirements/stages/*`、`docs/design/cli-command-reference.md` ほか stage 3 関連ドキュメント。
    - リスク: CLI 競合の取り込み漏れによる regressions、プレペア素材追加によるテスト環境依存、stage 番号の不整合。段階的に検証し、必要に応じて個別テストを追加する。
    - テスト方針: `uv run --extra dev pytest` を基本とし、CLI の主要テスト（`tests/test_cli_integration.py` など）を重点確認。必要に応じて `uv run pptx template ...` や `uv run pptx prepare ...` を実行し成果物のハッシュ・ログで確認する。
    - ロールバック方法: マージコミットを取り消して HEAD を `f8ce68a` へ戻し再検討する。部分的に問題がある場合は差分コミット単位で revert して調整する。
    - 承認メッセージ ID／リンク: user-20251104-plan-approval
- [x] 設計・実装方針の確定
  - メモ: テンプレ stage コマンドの統合仕様を main 側へ追従し、プレペア正規化導入後の CLI フローを branch 内で再確認済み。
- [x] ドキュメント更新（要件・設計）
  - メモ: README・design/cli-command-reference ほか stage 表記を最新仕様へ同期。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: origin/main のプレペア統合差分をマージし、`cli.py` の競合解消とテンプレ stage コマンドの統合動作を調整。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest` を実施し 162 件成功。CLI 統合テストを新仕様に合わせて更新済み。2025-11-04 に再マージ差分を確認し、`tests/test_cli_integration.py` の import 整合性を調整後に再実行して全件成功を確認。
- [x] ドキュメント更新
  - メモ: README / design / requirements の stage 表現を最新化。roadmap ほか追加更新なしを確認。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: Issue 番号確定後に更新する
- [x] PR 作成
  - メモ: PR #261 https://github.com/yurake/pptx_generator/pull/261（2025-11-03 完了）

## メモ
Plan 策定と承認手続き後に随時更新する
