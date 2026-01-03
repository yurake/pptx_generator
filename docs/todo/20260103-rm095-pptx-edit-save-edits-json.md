---
目的: RM-095 Stage5 edit で適用済み差分(JSON)を成果物として保存
関連ブランチ: feat/rm095-stage5-edit
関連Issue: #520
roadmap_item: RM-095 pptx edit
---

- [x] ブランチ作成・初期コミット・push
  - メモ: feat/rm095-stage5-edit を流用済み。コミット・push 完了。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済みPlan:
    - 対象整理（スコープ、対象ファイル、前提）: Stage5 edit に適用した差分を JSON として保存し、成果物に含める。現行の PPTX 出力に加えて JSON 出力を追加する。
    - ドキュメント／コード修正方針: 出力パスに `applied_edits.json` を保存し、/jobs 応答の artifacts に URL を追加する。必要に応じて OpenAPI と docs を更新。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo更新とPRレビューで共有。
    - 想定影響ファイル: src/pptx_generator/edit系処理、api artifacts周り、OpenAPI、テスト。
    - リスク: 出力パス仕様の整合、既存成果物の互換性。LLM未使用時もJSON出力するかの扱い。
    - テスト方針: pytestでJSON出力とartifacts反映を検証。既存テストが落ちないことを確認。
    - ロールバック方法: JSON保存処理とschema変更を元に戻す。
    - 承認メッセージ ID／リンク: ユーザー承認済み（本スレッド）。
- [x] 設計・実装方針の確定
  - メモ: 出力先 `PPTX_OUTPUT_ROOT/<transaction_id>/edit/<job_id>/applied_edits.json`。/jobs artifacts に JSON URL を含める方針で実装済み。
  - [x] 設計・実装方針メモの共有（本ToDoに記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: applied_edits.json を出力し artifacts に `edits_json_url` を追加。LLM/edits_json/edits 各経路で保存。CLI/async も共通パスで出力。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest -q` 実行。追加テストで JSON 出力と artifacts 反映を確認。カバレッジ 0.8607。
- [x] ドキュメント更新
  - メモ: OpenAPI（全体・edit専用）に edits_json_url を追記済み。その他は影響なしのため更新不要。
  - [x] docs/roadmap 配下（影響なしのため更新不要）
  - [x] docs/requirements 配下（影響なしのため更新不要）
  - [x] docs/design 配下（OpenAPI更新済み）
  - [x] docs/runbook 配下（影響なしのため更新不要）
  - [x] README.md / AGENTS.md（影響なしのため更新不要）
- [x] 関連Issue 行の更新
  - メモ: Issue 未作成のため未記入。発行後に更新。
- [x] チェックリスト整合確認
  - メモ: PR 作成以外を完了しチェック済み。
- [ ] PR 作成
  - メモ: 完了後に記載。自動更新に任せる。

## メモ
- 前提/制約: PPTX 出力は従来通り。JSON は追加成果物として扱う。
- 決定と理由: applied_edits.json を出力し artifacts で配信する方向。
- リスク(UNCONFIRMED): JSON出力が不要なケースの扱い、成果物URL命名の整合。
- Now/Next: Now=実装完了。Next=未更新ドキュメントの要否確認とPR作成。
- テスト実績/抜け: `uv run --extra dev pytest -q` 実行。警告は既存 (KeyboardInterrupt テスト) のみ。
