---
目的: RM-090 job_id リネームで execution_id を job_id へ統一し、外部公開キーを一貫させる
関連ブランチ: chore/rm090-job-id-rename
関連Issue: #433
roadmap_item: RM-090 job_id リネーム
---

- [ ] ブランチ作成・初期コミット・push
  - メモ: main から chore/rm090-job-id-rename を作成済み。初期コミットと push は未実施。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan 転記
    - 対象整理（スコープ、対象ファイル、前提）: execution_id を job_id にリネーム。対象は `src/pptx_generator/pipeline/base.py`（PipelineContext/生成箇所）、`src/pptx_generator/pipeline/trace.py`（trace 出力キー）、関連使用箇所、`tests/pipeline/test_pipeline_trace.py` などの検証コード。RM-090 方針に沿って job_id を公式キー化する。
    - ドキュメント／コード修正方針: パイプライン基盤のフィールド名・出力キー・参照文字列を job_id へ統一し、コードとテストを整合させる。CLI/API に execution_id 参照が残らないよう `rg` で確認する。
    - 確認・共有方法（レビュー、ToDo 更新など）: 作業ログは本 ToDo に記録し、変更内容は PR で共有。
    - 想定影響ファイル: `pipeline_trace.json` 出力、PipelineContext を経由する各ステージコード、関連テスト。
    - リスク: JSON キー変更による後方互換性低下、execution_id 残存による不整合。
    - テスト方針: `uv run --extra dev pytest tests/pipeline/test_pipeline_trace.py` を実行。時間があれば関連小粒度テストも確認。
    - ロールバック方法: リネーム変更を単一コミットにまとめ、問題時はそのコミットを revert。
    - 承認メッセージ ID／リンク: チャット承認（2025-12-17）
- [ ] 設計・実装方針の確定
  - メモ: Plan の方針をそのまま採用。追加論点なし。実装時に漏れがあれば本欄を更新してから続行する。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: PipelineContext の execution_id を job_id へリネームし、trace 出力キーとテストを更新。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/pipeline/test_pipeline_trace.py`（1 passed）/ `uv run --extra dev pytest --cov --cov-report=term --cov-report=xml`（全390件中 389 passed, 1 skipped, coverage 82%）
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
