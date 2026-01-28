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
- [x] 設計・実装方針の確定
  - メモ: LLM 出力の `contents` にスタイルタグを埋め込み、`fit` は boolean で受け取る。タグは `<b>`, `<i>`, `<color=...>`（色名 or `#RRGGBB`）を許容し、タグは同一行内で閉じる。適用は run 分割で行い、ベース書式に対して bold/italic/color を上書きする。`fit: true` で `MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE` を適用する。`applied_edits.json` はタグを除去した本文と `fit` を保存する。
  - [x] 設計・実装方針メモの共有（不要）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: edit AI プロンプト更新、スタイルタグのパースと適用、`fit` の auto-fit 反映、applied_edits のタグ除去保存を実装。
- [x] テスト・検証
  - メモ:
    - 自動テスト: `uv run --extra dev pytest tests/pipeline/test_text_edit.py tests/edit_ai/test_client.py tests/api/test_stages_edit_helpers.py`（23 passed）
    - ユーザー経路の手動確認（必要な場合）: stage1-5 の CLI を順に実行（PPTX_LLM_PROVIDER=aws-claude）
      - Stage1: `uv run pptx template samples/templates/dynamic_template.pptx --mode dynamic`（output/template, warnings=0）
      - Stage2: `uv run pptx prepare samples/input/pitch.md --mode dynamic`（output/prepare, aws-claude 実行）
      - Stage3: `uv run pptx compose output/template/jobspec.json --prepare-cards output/prepare/prepare_card.json`（output/compose, aws-claude 実行）
      - Stage4: `uv run pptx gen output/compose/generate_ready.json`（output/gen, rendering warnings=2）
      - Stage5 (LLM): `uv run pptx edit output/gen/proposal.pptx --output output/edit/proposal_llm.pptx`（適用件数=0）
      - Stage5 (明示差分): `uv run pptx edit output/gen/proposal.pptx --edits-json /tmp/edit_style_edits.json --output output/edit/proposal_styled.pptx`（適用件数=1）
    - 生成物の確認があれば、その方法と結果: output 配下の成果物生成を確認
- [x] ドキュメント更新
  - メモ: stage-05-edit と CLI リファレンスを更新。その他は更新不要。
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下（更新不要）
  - [x] docs/requirements 配下（stage-05-edit.md を更新）
  - [x] docs/design 配下（cli-command-reference.md を更新）
  - [x] docs/runbook 配下（更新不要）
  - [x] README.md / AGENTS.md（更新不要）
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
  - Now/Next: Now=テスト・UAT完了 / Next=結果共有とPR準備
  - テスト実績/抜け: `uv run --extra dev pytest tests/pipeline/test_text_edit.py tests/edit_ai/test_client.py tests/api/test_stages_edit_helpers.py`（23 passed）
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
