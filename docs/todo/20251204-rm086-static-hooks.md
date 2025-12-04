---
目的: RM-086 静的テンプレ外部フック統合の準備
関連ブランチ: docs/rm086-static-hooks-prep
関連Issue: #368
roadmap_item: RM-086 静的テンプレ外部フック統合
---

- [x] ブランチ作成・初期コミット・push
  - メモ: docs/rm086-static-hooks-prep を main から切り、初期コミットを push 済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: CLI 静的モード時に外部フックを stage ごと・スライドごとに解決する仕組みを追加し、テンプレ ID（PPTX ファイル名由来）ごとの `external/<template_id>/hooks.json` を解釈できるようにする。Stage 1〜4 の既存コマンドにフック実行ポイントを挿入し、未定義時は従来処理を維持する。スライド単位のフック指定は `スライド番号_レイアウト名` 規則で扱う。
    - ドキュメント／コード修正方針: `src/pptx_generator/cli.py` および各ステージコマンド生成関数へフック実行ロジックを追加し、新しいヘルパーモジュールで設定読み込み・実行を実装。外部設定スキーマと運用手順を `docs/design` / `docs/policies` に反映し、ToDo にも整合を記載。
    - 確認・共有方法（レビュー、ToDo 更新など）: 実装差分は PR でレビュー。ToDo を随時更新し、重要決定は `docs/notes/20251204-rm086-static-hooks.md` に追記。
    - 想定影響ファイル: `src/pptx_generator/cli.py`, `src/pptx_generator/cli_commands/*`, 新規 `cli_hooks` モジュール群, `docs/design`, `docs/policies`, テストコード（`tests/cli`, `tests/integration` など）。
    - リスク: 外部フック失敗時の CLI 停止に備えたエラーハンドリング、`external/` 不在時のフォールバック、スライド別設定の複雑化、テスト環境での `external` モック管理。
    - テスト方針: ユニットテストで設定パースと優先順位、結合テストでダミーフックを呼び出す CLI フロー、エラーパス検証、`uv run --extra dev pytest` による回帰確認。
    - ロールバック方法: 実装コミットを `git revert` で戻し、追加ドキュメントも同ブランチで削除。外部設定を利用しないことで旧フローへ戻せる。
    - 承認メッセージ ID／リンク: （本チャットでの承認）
- [x] 設計・実装方針の確定
  - メモ: CLI 全ステージ（template/prepare/compose/mapping/gen）で静的モード時に `external/<template_id>/hooks.json` を解釈し、ステージ前後のフックとスライド別フックを呼び出す設計に決定。テンプレート ID は PPTX ファイル名 stem から導出し、スライドキーは `.pptx/extract/prompts/01_system-layout.md` と同じ `NN_slug` 形式で揃える。ENV 変数一覧（PPTX_STAGE など）を整理し、ステージ後に生成物パスを追加で渡す。TODO: ドキュメントへ使用方法を追記。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
    - メモ: 詳細は `docs/notes/20251204-rm086-static-hooks.md` に会話ログとして記録済み。今後の追記は同ファイルへ集約する。
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: `src/pptx_generator/cli_hooks/*` を新設し、`cli_commands` 各ステージにフック制御を組み込み済み（コミット: `feat(cli): add external hook support for static mode`, `feat(cli): invoke slide-level hooks after stages`）。ドキュメント反映は未実施。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/cli/test_cli_hooks.py` を実行し、外部フック管理・スライドキー生成・template_id ヘルパーのユニットテスト（全6件）を追加。カバレッジ XML を再生成済み。
- [ ] 外部フック運用検証
  - メモ: `external/<template_id>` にダミー `hooks.json` とスクリプトを配置し、`uv run pptx template/prepare/... --mode static` でステージ・スライドフックが発火することを確認する。
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
