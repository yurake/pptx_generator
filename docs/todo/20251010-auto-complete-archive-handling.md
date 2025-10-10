---
目的: auto_complete_todo.py でアーカイブ済み ToDo も成功扱いできるよう判定ロジックを改善する
関連ブランチ: fix/auto-complete-archive
関連Issue: #144
roadmap_item: RM-015 ワークフロー自動化基盤整備
---

- [x] まずはブランチ作成
- [x] auto_complete_todo.py の現行仕様とエラー再現条件を調べる
  - メモ: `main()` の `todo_path.exists()` で存在しないと `FileNotFoundError` を送出しており、`docs/todo/archive/` 配下のファイルのみを指定すると現在はエラーでワークフローが停止する。`process_todo()` でも `[ ]` が無いと即アーカイブ扱いになるため、成功判定の分岐整理と、既にアーカイブ済みの場合のショートサーキット処理が必要。
- [x] アーカイブ済み ToDo を成功条件として判定するロジックとメッセージを実装する
  - メモ: `main()` に `docs/todo/archive/` 配下を検出してスキップ扱いにする分岐を追加し、引数にアクティブ側パスを渡してもアーカイブ済みが見つかれば成功ログを出して終了するよう更新した。
- [x] 単体テストまたはスクリプト実行で想定パスの動作を検証する
  - メモ: pytest で `docs/todo/archive/` を直接指定するケースとアーカイブ側フォールバックを踏むケースを追加し、どちらも INFO ログを出して異常終了しないことを確認した。
- [ ] ドキュメントとロードマップ、ToDo の相互リンクを更新する
  - メモ: docs/roadmap/README.md や関連メモを整備する
- [x] PR 作成
  - メモ: PR #146 https://github.com/yurake/pptx_generator/pull/146（2025-10-10 完了）

## メモ
- GitHub Actions の todo-auto-complete ワークフローで参照するファイル構造を整理し、docs/todo/archive/ 配下の扱いを明記する
  - 再現状況: main ブランチで `uv run scripts/auto_complete_todo.py --todo docs/todo/archive/<対象>.md --pr-number 1 --pr-url <dummy> --dry-run` を実行すると、`FileNotFoundError: docs/todo/archive/<対象>.md が見つかりません` が発生してワークフローが停止する。
  - 対応方針メモ: 存在チェックでアーカイブ側を許容する分岐を追加し、`docs/todo/archive/` に既に移動済みの場合は成功ログを出して早期リターンする。また、`process_todo()` の `[ ]` 判定を維持しつつ、アーカイブ済みファイルは再アーカイブしないようにスキップフローを追加する。
