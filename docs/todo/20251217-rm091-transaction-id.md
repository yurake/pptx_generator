---
目的: RM-091 transaction_id 導入で 4 stage を跨ぐ一意 ID を公式化し、job_id を束ねて追跡できるようにする
関連ブランチ: chore/rm091-transaction-id
関連Issue: #435
roadmap_item: RM-091 transaction_id 導入
---

- [x] ブランチ作成・初期コミット・push
  - メモ: main から chore/rm091-transaction-id を作成済み。初期コミットと push は未実施。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan 転記
    - 対象整理（スコープ、対象ファイル、前提）: PipelineContext へ transaction_id を追加し生成・保持・伝搬する。`src/pptx_generator/pipeline/base.py` でフィールド追加、`src/pptx_generator/pipeline/trace.py` に transaction_id を含める。入口層（CLI/API）で未指定なら生成・指定時は継続利用できる経路を最小で整備する。`tests/pipeline/test_pipeline_trace.py` などトレース検証系を更新し、生成・保持を確認するケースを追加する。
    - ドキュメント／コード修正方針: job_id は従来どおりリクエスト単位で発行し、trace/audit には transaction_id とセットで残す。CLI で指定経路がなければ内部生成と trace 反映を優先し、外部IFへの露出は最小の追加に留める。`rg` で transaction_id / job_id の整合を確認する。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo に進捗を記録し、PR で共有する。
    - 想定影響ファイル: PipelineContext / pipeline_trace 出力、コンテキスト構築を行う入口層、トレース関連テスト。
    - リスク: JSON 形式変更による後方互換性への影響、transaction_id 伝搬漏れ。
    - テスト方針: 最小で `uv run --extra dev pytest tests/pipeline/test_pipeline_trace.py` を実行。余力があれば関連小粒度テストを追加・実行する。
    - ロールバック方法: 変更をまとまったコミットにし、問題時はそのコミットを revert できる形にする。
    - 承認メッセージ ID／リンク: チャット承認（2025-12-17 RM-091）
- [x] 設計・実装方針の確定
  - メモ: Plan 方針そのまま適用。PipelineContext に transaction_id を追加し、trace とテストで併記。入口層は最小で内部生成を優先し、追加の指定経路は後続で検討。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: PipelineContext に transaction_id を追加し、pipeline_trace 出力とテストを更新。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/pipeline/test_pipeline_trace.py`（1 passed）
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
