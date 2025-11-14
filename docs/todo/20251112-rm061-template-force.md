---
目的: Force オプションでテンプレート検証をスキップできるようにし、緊急時もテンプレ工程を継続可能にする
関連ブランチ: feat/rm061-usage-tags-governance
関連Issue: #288
roadmap_item: RM-061 usage_tags ガバナンス強化
---

- [x] ブランチ作成と初期コミット
  - メモ: 既存ブランチ `feat/rm061-usage-tags-governance` を継続利用
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan を反映
    - 対象整理（スコープ、対象ファイル、前提）: `pptx template` コマンドのテンプレ抽出ワークフロー。`--force/-f` 指定時のみ LayoutValidation をスキップする。既存の `tpl-extract` など他コマンドには影響させない。
    - ドキュメント／コード修正方針: `src/pptx_generator/cli.py` と `pipeline/template_extractor.py` にフラグを追加し、バリデーション呼び出し可否を制御。テストは `tests/test_cli_integration.py` を中心に整備。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo を更新し、PR で差分とテスト結果を共有。
    - 想定影響ファイル: `src/pptx_generator/cli.py`, `src/pptx_generator/pipeline/template_extractor.py`, `tests/test_cli_integration.py`。
    - リスク: 検証を飛ばすことで不正なレイアウトが流通する可能性。force は緊急時のみ利用する前提で案内し、メッセージで注意喚起する。
    - テスト方針: `pytest tests/test_cli_integration.py` を実行。force 指定時に LayoutValidation 呼び出しがスキップされることをモンキーパッチで検証。
    - ロールバック方法: 追加した `force` フラグと関連分岐を削除し、既存実装に戻す。
    - 承認メッセージ ID／リンク: ユーザー「ok」メッセージ
- [ ] 設計・実装方針の確定
  - メモ: 
- [ ] ドキュメント更新（要件・設計）
  - メモ: 
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
- [x] 実装
  - メモ: `--force` オプション追加と検証スキップ処理、出力メッセージ調整。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_cli_integration.py`
- [ ] ドキュメント更新
  - メモ: 
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次アクション条件をここに記載する。
