---
目的: PR #262 のレイアウト検証エラー検出処理の実装を整備する
関連ブランチ: feat/rm046-brief-automation
関連Issue: #263
roadmap_item: RM-046 生成AIブリーフ構成自動化
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/rm046-brief-automation を main から作成済み。初期コミットは既存機能拡張向けのため本作業での追加コミットは未作成。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: `tpl_extract` サブコマンド内のレイアウト検証結果ハンドリングを改善し、エラー件数が 1 件以上の場合は終了コード 6 で失敗終了させる。付随して CLI 統合テストに検証ケースを追加する。
    - ドキュメント／コード修正方針: `src/pptx_generator/cli.py` で検証結果を確認し `click.exceptions.Exit(code=6)` を発生させるロジックを追加。`tests/test_cli_integration.py` に失敗ケースのテストを新設する。必要に応じて logger 出力の順序を微調整。
    - 確認・共有方法（レビュー、ToDo 更新など）: Plan 承認済み。作業完了後に当該 ToDo を更新し、PR 説明へ Plan 承認メッセージを記載予定。
    - 想定影響ファイル: `src/pptx_generator/cli.py`, `tests/test_cli_integration.py`
    - リスク: 自動化フローで従来成功していたケースが失敗扱いになる可能性があるが、レイアウトエラー検知の意図に沿う挙動であり受容。想定外の終了コード変化がないようテストで確認。
    - テスト方針: `pytest tests/test_cli_integration.py::test_cli_tpl_extract_validation_failure_exits_with_error`（新設）を実行し、終了コードとメッセージを確認。
    - ロールバック方法: 追加ロジックとテストを差分撤回し、`tpl_extract` の処理を元に戻す。
    - 承認メッセージ ID／リンク: （この会話でのユーザー承認。CLI 環境上でメッセージ ID 取得不可のため作業ログで補足）
- [x] 設計・実装方針の確定
  - メモ: Plan で整理した方針（CLI 側でエラー件数を監視し exit code 6 を返す）の通り実装し、追加検討事項は発生せず。
- [x] ドキュメント更新（要件・設計）
  - メモ: コード修正のみで既存要件／設計ドキュメントに変更は不要と判断。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `tpl_extract` にレイアウト検証エラー時の終了コード 6 返却処理を追加し、`click.exceptions.Exit` の再ラップを防ぐガードを導入。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_cli_integration.py::test_cli_tpl_extract_validation_failure_exits_with_error` / `uv run --extra dev pytest`
- [x] ドキュメント更新
  - メモ: 影響範囲に追加ドキュメントはなく、既存資料の整合も確認済み。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [x] PR 作成
  - メモ: PR #262 https://github.com/yurake/pptx_generator/pull/262（2025-11-03 完了）

## メモ
