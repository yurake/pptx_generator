---
目的: auto_complete_todo.py でアーカイブ済み ToDo も成功扱いできるよう判定ロジックを改善する
関連ブランチ: fix/auto-complete-archive
関連Issue: 未作成
roadmap_item: RM-015 ワークフロー自動化基盤整備
---

- [ ] まずはブランチ作成
- [ ] auto_complete_todo.py の現行仕様とエラー再現条件を調べる
  - メモ: アーカイブ済みファイル検出可否と GitHub Actions 上の動作を確認する
- [ ] アーカイブ済み ToDo を成功条件として判定するロジックとメッセージを実装する
  - メモ: 対象ファイルの存在確認を追加し、必要に応じてログ出力を調整する
- [ ] 単体テストまたはスクリプト実行で想定パスの動作を検証する
  - メモ: モック入力とアーカイブファイルを用いたケースを追加する
- [ ] ドキュメントとロードマップ、ToDo の相互リンクを更新する
  - メモ: docs/roadmap/README.md や関連メモを整備する
- [ ] PR 作成
  - メモ: PR を作成したら番号と URL を記入する

## メモ
- GitHub Actions の todo-auto-complete ワークフローで参照するファイル構造を整理し、docs/todo/archive/ 配下の扱いを明記する
