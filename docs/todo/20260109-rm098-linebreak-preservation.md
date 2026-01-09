---
目的: RM-098 改行・空行の保持
関連ブランチ: feat/rm098-linebreak-preservation
関連Issue: 未作成
roadmap_item: RM-098 改行・空行の保持
---

- [x] ブランチ作成・初期コミット・push
  - メモ: feat/rm098-linebreak-preservation を upstream/main から作成。初期コミットと origin への push 済み。
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: 改行・空行保持の共通ルールを定め、入力（HTML/Markdown/AI 応答）から prepare/compose/render まで空行が欠落しないように整える。対象候補は `src/pptx_generator/content_import/service.py`, `src/pptx_generator/prepare/source.py`, `src/pptx_generator/cli_handlers/prepare_inputs.py`, `src/pptx_generator/pipeline/prepare_normalization.py`, `src/pptx_generator/slide_ai/response_parser.py`, `src/pptx_generator/pipeline/draft_structuring/slide_elements.py`。前提はローカルで再現確認する。
    - ドキュメント／コード修正方針: 空行が落ちる正規化を最小化し、空行保持の共通ルールと分割処理を統一する。必要なら共通ヘルパーを追加する。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo を更新しつつ PR テンプレに沿って共有する。
    - 想定影響ファイル: `src/pptx_generator/content_import/service.py`, `src/pptx_generator/prepare/source.py`, `src/pptx_generator/cli_handlers/prepare_inputs.py`, `src/pptx_generator/pipeline/prepare_normalization.py`, `src/pptx_generator/slide_ai/response_parser.py`, `src/pptx_generator/pipeline/draft_structuring/slide_elements.py`, `tests/prepare/test_prepare_source_document.py`, `tests/slide_ai/test_response_parser.py`
    - リスク: 空行の保持による行数制約・レンダリング高さの変化
    - テスト方針: 既存テストに空行保持のケースを追加し、prepare/slide_ai の正規化を確認する。
    - ロールバック方法: 該当コミットの revert
    - 承認メッセージ ID／リンク: ユーザー「OK！」
- [ ] 設計・実装方針の確定
  - メモ: Plan 承認内容を踏まえた設計・実装方針をここに記載し、ユーザー確認が必要な論点があれば列挙する。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [ ] 実装
  - メモ: 実装範囲や未対応事項があれば記載する
- [ ] テスト・検証
  - メモ: 実施したテスト内容と結果を記入する
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
  - 前提/制約: 再現確認はローカルで実施し、入力は HTML/Markdown/AI 応答を想定する。
  - 決定と理由: 空行を落とさない共通ルールを採用し、パイプライン全体の分割処理を統一する。
  - リスク(UNCONFIRMED): 空行保持で行数制約や高さ計算に影響する可能性。
  - Now/Next: 仕様・方針の確定 → 実装とテスト追加。
  - テスト実績/抜け: 未実施。
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
