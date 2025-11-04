---
目的: PR #266 の Codex レビュー指摘に対応し、generate_ready.json の template_path を持ち運び可能な形で保存できるようにする
関連ブランチ: feat/rm049-pptx-gen-scope
関連Issue: #266
roadmap_item: RM-049 pptx gen スコープ最適化
---

- [x] ブランチ作成と初期コミット
  - メモ: main から feat/rm049-pptx-gen-scope を作成済み。初期コミットは既存タスクで追加済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: LibreOffice 未導入環境で `tests/test_cli_integration.py::test_cli_gen_pdf_only` が失敗する事象を解消し、LibreOffice が検出できない場合はテストを skip させる。対象ファイルは `tests/test_cli_integration.py`。
    - ドキュメント／コード修正方針: テスト側に LibreOffice 存在判定ヘルパーを追加し、未導入時に `pytest.skip` を発生させる。LibreOffice が見つかる環境では既存のモック挙動を保つ。
    - 確認・共有方法（レビュー、ToDo 更新など）: 対象テストを個別実行して結果を ToDo に反映し、CI での失敗が解消されたことを報告する。
    - 想定影響ファイル: `tests/test_cli_integration.py`
    - リスク: LibreOffice 判定が誤検出すると想定外の skip/実行が発生するため `LIBREOFFICE_PATH` と `shutil.which("soffice")` 双方をチェックする。
    - テスト方針: `uv run --extra dev pytest tests/test_cli_integration.py::test_cli_gen_pdf_only`
    - ロールバック方法: `git checkout -- tests/test_cli_integration.py`
    - 承認メッセージ ID／リンク: ユーザー承認（"ok" メッセージ）
- [ ] 設計・実装方針の確定
  - メモ: 必要に応じてレビュー内容を整理する。
- [ ] ドキュメント更新（要件・設計）
  - メモ: 要件・設計の更新が必要な場合は記録する。
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: 実装範囲と留意点を記録する。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_cli_integration.py::test_cli_gen_pdf_only` を実行し、LibreOffice 利用環境でパスすることを確認。LibreOffice 未導入環境では skip となる想定を共有。
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理する。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: Issue 番号の更新状況を記録する。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録する。

## メモ
