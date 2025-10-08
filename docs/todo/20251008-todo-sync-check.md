---
目的: ToDo 同期ワークフローの多ファイル対応検証
担当者: Codex
関連ブランチ: docs/todo-sync-check
期限: 2025-10-15
関連Issue: #102
---

- [ ] docs/todo/ 配下の現行ファイルを棚卸しし、対象一覧を確定する
  - `ls docs/todo` で一覧取得、`archive/` 含めてメモに列挙
  - template.md は同期対象外であることを README と照合
- [ ] 代表ファイルを複製し、1 Issue にタスク一覧が反映されることを確認する
  - `cp docs/todo/template.md docs/todo/20251008-sync-sample.md`
  - front matter を埋めてタスクタイトルを編集、`git commit` して push
  - push 後に `todo-sync / Sync ToDo → Issues` が走り、1 件の Issue にチェックボックスが生成されるか確認
- [ ] 複数ファイル並行時にタスクが混在しないことを確認する
  - 別ファイル `docs/todo/20251008-sync-parallel.md` を追加し同様に push
-  - Actions ログで各ファイルの処理結果を確認し、GitHub Issues 上で `<!-- todo-path: ... -->` マーカーが適切に設定されていることをチェック
- [ ] 完了済み ToDo を archive/ へ移動した際も同期されるか確認する
  - テスト済みファイルを `git mv docs/todo/20251008-sync-sample.md docs/todo/archive/`
  - push 後の Actions 実行で同ファイルが引き続き処理対象となり、親 Issue 参照が維持されるか確認
- [ ] `[skip md->issues]` コミットで md→Issues の同期が抑止されるか確認する
  - 対象ファイルに軽微な変更を入れたコミットを `[skip md->issues]` 付きで push
  - Actions ログで `Sync ToDo → Issues` ジョブがスキップされることを確認
- [ ] 検証結果を docs/notes/ へ記録し、後続改善タスクを洗い出す
  - 成果・問題点・残課題を `docs/notes/20251008-todo-sync-test-coverage.md` に追記
  - 改善が必要な項目は別の ToDo または Issue として整理

## メモ
- ラベル命名や親 Issue のフォーマットに変更が必要になった場合は別タスク化する。
