---
目的: RM-095 PPTX edit コマンドの PPTX 引数を必須の位置引数へ変更する
関連ブランチ: feat/rm095-stage5-edit
関連Issue: <#123 の形式で記載 / 未作成の場合は作成次第更新>
roadmap_item: RM-095 Stage5 PPTX 編集反映
---

- [x] ブランチ作成・初期コミット・push
  - メモ: 既存ブランチ feat/rm095-stage5-edit を流用。初期コミット済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: `pptx edit` の PPTX を位置引数必須に変更し、--pptx-path は廃止。README/notes の例を追随。互換性: 既存スクリプトで --pptx-path を使っている場合は要修正。
- [x] 設計・実装方針の確定
  - メモ: click 引数を `pptx_path` 位置引数に変更、ヘルプ/README で位置引数記載に統一。tests CLI サンプルも更新。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: `src/pptx_generator/cli_commands/edit.py` を位置引数化。README/notes を位置引数例に差し替え。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/pipeline/test_text_edit.py`（6件成功）。
- [x] ドキュメント更新
  - メモ: README のコマンド例と notes を位置引数に更新。その他は影響なしのため変更不要。
  - [x] docs/roadmap 配下（影響なし）
  - [x] docs/requirements 配下（影響なし）
  - [x] docs/design 配下（影響なし）
  - [x] docs/runbook 配下（影響なし）
  - [x] README.md / AGENTS.md（例を更新済み）
- [x] 関連Issue 行の更新
  - メモ: Issue 未作成のため追って更新。
- [x] チェックリスト整合確認
  - メモ: 残タスクは PR 作成のみ。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載。

## メモ
- 前提/制約: 既存 CLI 互換への影響があるため非推奨オプションの扱いを検討。ブランチは既存を流用。
- 決定と理由: 未定（Plan 承認後に更新）
- リスク(UNCONFIRMED): 既存スクリプト/ドキュメントの --pptx-path 利用が失敗する可能性。ヘルプ/README も更新必須。
- Now/Next: Now=Plan 作成・承認待ち。Next=設計方針確定→実装着手。
- テスト実績/抜け: なし（これから実施）
