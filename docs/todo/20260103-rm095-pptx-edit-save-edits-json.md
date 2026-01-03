---
目的: RM-095 Stage5 edit で適用済み差分(JSON)を成果物として保存
関連ブランチ: feat/rm095-stage5-edit
関連Issue: #520
roadmap_item: RM-095 pptx edit
---

- [ ] ブランチ作成・初期コミット・push
  - メモ: feat/rm095-stage5-edit を流用。初期コミット済み。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: 承認済みPlan:
    - 対象整理（スコープ、対象ファイル、前提）: Stage5 edit に適用した差分を JSON として保存し、成果物に含める。現行の PPTX 出力に加えて JSON 出力を追加する。
    - ドキュメント／コード修正方針: 出力パスに `applied_edits.json` を保存し、/jobs 応答の artifacts に URL を追加する。必要に応じて OpenAPI と docs を更新。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo更新とPRレビューで共有。
    - 想定影響ファイル: src/pptx_generator/edit系処理、api artifacts周り、OpenAPI、テスト。
    - リスク: 出力パス仕様の整合、既存成果物の互換性。LLM未使用時もJSON出力するかの扱い。
    - テスト方針: pytestでJSON出力とartifacts反映を検証。既存テストが落ちないことを確認。
    - ロールバック方法: JSON保存処理とschema変更を元に戻す。
    - 承認メッセージ ID／リンク: ユーザー承認済み（本スレッド）。
- [ ] 設計・実装方針の確定
  - メモ: 出力先案 `PPTX_OUTPUT_ROOT/<transaction_id>/edit/<job_id>/applied_edits.json`。/jobs artifacts に JSON URL を含める方向。OpenAPI も最小反映する。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [ ] 実装
  - メモ: 適用済み edits を保存する処理と artifacts への URL 追加を行う。必要なら CLI/async 実行パスも確認。
- [ ] テスト・検証
  - メモ: /edit ジョブ完了後に JSON 出力が存在し内容が適用済み edits と一致すること、/jobs artifacts に URL が載ることを確認。既存テストへの影響なしを確認。
- [ ] ドキュメント更新
  - メモ: 変更点を設計/API docs に反映予定。必要な箇所のみ更新。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: Issue 未作成のため未記入。発行後に更新。
- [ ] チェックリスト整合確認
  - メモ: 親子チェック漏れがないか後続で確認。
- [ ] PR 作成
  - メモ: 完了後に記載。自動更新に任せる。

## メモ
- 前提/制約: PPTX 出力は従来通り。JSON は追加成果物として扱う。
- 決定と理由: applied_edits.json を出力し artifacts で配信する方向。
- リスク(UNCONFIRMED): JSON出力が不要なケースの扱い、成果物URL命名の整合。
- Now/Next: Now=ToDo作成。Next=設計詳細を詰めて実装。
- テスト実績/抜け: 未着手。
