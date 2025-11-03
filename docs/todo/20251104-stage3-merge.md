---
目的: mainの工程3大型変更をfeat/rm-051-template-integrationへ取り込む
関連ブランチ: feat/rm-051-template-integration
関連Issue: #265
roadmap_item: RM-051 テンプレ工程統合集約
---

- [x] ブランチ作成と初期コミット
  - メモ: mainから作成済みのfeat/rm-051-template-integrationを継続利用。初期コミットは2025-11-03のToDo追加。
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: `feat/rm-051-template-integration` に origin/main の工程3（ブリーフ統合）変更を取り込み、CLI・パイプライン・tests・docs を最新化する。工程1統合実装との整合を維持する。origin/main を最新取得済み。`gh issue list` は TLS エラーで確認不可。
    - ドキュメント／コード修正方針: まず `git merge origin/main` で Stage3 ブリーフ機能の差分を取り込み、`src/pptx_generator/cli.py` を中心に競合を解消する。`src/pptx_generator/brief/*` と `pipeline/brief_normalization.py` の追加を正しく統合し、テストや README・requirements/design/notes 等の工程表記も反映させる。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo へ進捗を逐次記録し、Plan 承認メッセージ ID を記録。作業完了時に README と docs 更新内容を自己チェックし、必要に応じて user へ共有する。
    - 想定影響ファイル: `src/pptx_generator/cli.py`、`src/pptx_generator/brief/**/*`、`src/pptx_generator/pipeline/brief_normalization.py`、`tests/test_cli_integration.py`、`tests/test_cli_content.py`、`tests/test_cli_outline.py`、`tests/test_mapping_step.py`、`README.md`、`docs/requirements/stages/*`、`docs/design/cli-command-reference.md` ほか工程3関連ドキュメント。
    - リスク: CLI 競合の取り込み漏れによる regressions、ブリーフ素材追加によるテスト環境依存、工程番号の不整合。段階的に検証し、必要に応じて個別テストを追加する。
    - テスト方針: `uv run --extra dev pytest` を基本とし、CLI の主要テスト（`tests/test_cli_integration.py` など）を重点確認。必要に応じて `uv run pptx template ...` や `uv run pptx brief ...` を実行し成果物のハッシュ・ログで確認する。
    - ロールバック方法: マージコミットを取り消して HEAD を `f8ce68a` へ戻し再検討する。部分的に問題がある場合は差分コミット単位で revert して調整する。
    - 承認メッセージ ID／リンク: user-20251104-plan-approval
- [x] 設計・実装方針の確定
  - メモ: テンプレ工程コマンドの統合仕様を main 側へ追従し、ブリーフ正規化導入後の CLI フローを branch 内で再確認済み。
- [x] ドキュメント更新（要件・設計）
  - メモ: README・design/cli-command-reference ほか工程表記を最新仕様へ同期。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: origin/main のブリーフ統合差分をマージし、`cli.py` の競合解消とテンプレ工程コマンドの統合動作を調整。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest` を実施し 162 件成功。CLI 統合テストを新仕様に合わせて更新済み。
- [x] ドキュメント更新
  - メモ: README / design / requirements の工程表現を最新化。roadmap ほか追加更新なしを確認。
  - [ ] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: Issue 番号確定後に更新する
- [ ] PR 作成
  - メモ: PR 作成時に番号とURLを記録する

## メモ
Plan 策定と承認手続き後に随時更新する
