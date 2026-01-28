---
目的: RM-100 編集指示スタイリング対応
関連ブランチ: feat/rm100-edit-styling
関連Issue: 未作成
roadmap_item: RM-100 編集指示スタイリング対応
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ名 `feat/rm100-edit-styling` / 初期コミットは RM-100 準備の ToDo 作成 / push 済み
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan
    - 対象整理（スコープ、対象ファイル、前提): Stage5 edit のスタイリング指示対応（太字/斜体/色/枠内収容）を実装。日本語指示を前提に LLM で解釈し、内部表現として適用する。
    - ドキュメント／コード修正方針: edit AI のプロンプト/パースと text_edit の適用ロジックを拡張し、applied_edits の保存形式も更新する。ドキュメントは stage-05-edit と CLI リファレンスを更新。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo 更新と差分共有で確認する。
    - 想定影響ファイル: `src/pptx_generator/edit_ai/prompts.py`, `src/pptx_generator/edit_ai/client.py`, `src/pptx_generator/pipeline/text_edit.py`, `src/pptx_generator/pipeline/edit_runner.py`, `docs/requirements/stages/stage-05-edit.md`, `docs/design/cli/cli-command-reference.md`, `tests/pipeline/test_text_edit.py`, `tests/edit_ai/test_client.py`
    - リスク: auto-fit によりフォントが過度に縮小される可能性。色名の解釈ゆれは未適用として警告扱いにする。
    - テスト方針: 既存 unit に装飾/auto-fit のテストを追加。必要に応じて CLI の簡易 UAT を実施。
    - ロールバック方法: 関連コミットを `git revert` し、従来のテキスト差し替えに戻す。
    - 承認メッセージ ID／リンク: ユーザー OK（2026-01-28）
- [ ] 設計・実装方針の確定
  - メモ: Plan 承認内容を踏まえた設計・実装方針をここに記載し、ユーザー確認が必要な論点があれば列挙する。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [ ] 実装
  - メモ: 実装範囲や未対応事項があれば記載する
- [ ] テスト・検証
  - メモ: 以下を簡潔に記載する
    - 自動テスト: 実行コマンドと結果（例: `uv run --extra dev pytest`, `diff-cover`）
    - ユーザー経路の手動確認（必要な場合）: 代表手順1本のコマンドと結果（例: docker build/run/curl, CLI compose→gen）
    - 生成物の確認があれば、その方法と結果
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 連続性メモ（短文化し、更新があれば上書きする）※設計確定・実装完了・テスト完了・PR作成前後など状態変化のたびに更新
  - 前提/制約: edit 指示からスタイリングと文字サイズ調整を反映する。
  - 決定と理由: 日本語指示を前提に LLM で解釈し、内部マークアップを適用する。
  - リスク(UNCONFIRMED): auto-fit による可読性低下の可能性。
  - Now/Next: Now=Plan 承認 / Next=設計・実装方針の確定
  - テスト実績/抜け: 未実施
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
