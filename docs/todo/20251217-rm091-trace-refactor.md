---
目的: RM-091 で pipeline_trace を全ステージに統一し、PipelineContext を共通化して job_id/transaction_id を横断管理する
関連ブランチ: chore/rm091-transaction-id
関連Issue: #436
roadmap_item: RM-091 transaction_id 導入
---

- [ ] ブランチ作成・初期コミット・push
  - メモ: ブランチ chore/rm091-transaction-id を継続利用
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan を転記
    - 対象整理（スコープ、対象ファイル、前提）: template/prepare/compose/gen の CLI ハンドラを PipelineContext ベースに揃え、各ステージで pipeline_trace.json を出力する。job_id はステージごとに発行、transaction_id はステージ横断で共通。コンテキスト初期化と trace 出力の共通化を行い、CLI で transaction_id 指定を受け取れるようにする。
    - ドキュメント／コード修正方針: コンテキスト生成のヘルパを用意し、各ステージ終了時に write_pipeline_trace を呼ぶ。出力は stage ディレクトリ配下に配置。必要に応じて CLI オプションを追加し、従来挙動との互換性に注意する（出力ファイル増加は許容）。
    - 確認・共有方法: 本 ToDo に進捗を記録し、PR で変更概要・影響範囲を共有。
    - 想定影響ファイル: `src/pptx_generator/cli_handlers/template_*.py`, `prepare.py`, `compose.py`, `rendering.py`、`pipeline/base.py`, `pipeline/trace.py`、CLI コマンド定義部、関連テスト。
    - リスク: CLI 互換性（引数追加/出力構成変更）、コンテキスト生成漏れ、外部スクリプト依存の破壊。LLM 呼び出しによるレート制限影響。
    - テスト方針: `uv run --extra dev pytest tests/pipeline/test_pipeline_trace.py` を最小実行。時間許せば `uv run --extra dev pytest` 全体または統合テストを実施。
    - ロールバック方法: コンテキスト統一をまとまったコミットにし、revert 可能な単位で管理する。
    - 承認メッセージ ID／リンク: チャット承認（RM-091 trace リファクタ）
- [ ] 設計・実装方針の確定
  - メモ: Plan に基づき、CLI オプション追加とコンテキスト初期化ヘルパの形を決めて記載する
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
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- UAT 予定: ステージごとに pipeline_trace.json が出力されることを確認（静的/動的モード）。出力先は各ステージの output ディレクトリ配下。
