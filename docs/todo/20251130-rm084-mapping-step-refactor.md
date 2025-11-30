---
目的: RM-084 CLI/Pipeline リファクタビリティ向上 - `MappingStep.run` の責務分離とヘルパー抽出
関連ブランチ: chore/rm084-cli-refactorability
関連Issue: #344
roadmap_item: RM-084 CLI/Pipeline リファクタビリティ向上
---

- [ ] ブランチ作成・初期コミット・push
  - メモ: chore/rm084-cli-refactorability を main から作成済み。リモート未 push（環境制約のためローカル作業継続）。既存ブランチを流用し mapping リファクタへ拡張予定。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: `src/pptx_generator/pipeline/mapping.py` の `MappingStep.run` を中心に、ワークアイテム構築・スライド処理・成果物出力処理をヘルパーへ分離する。既存の出力 JSON 構造・例外コード・外部依存は変更しない。
    - ドキュメント／コード修正方針: `MappingStep.run` をフロー制御のみに絞り、ランタイム状態を保持する小さなデータクラス／ヘルパー `_build_work_items`, `_process_work_item`, `_write_outputs`（名称仮）へ抽出。必要に応じて `mapping.py` 内に新規補助クラスを追加。ドキュメント側はリファクタメモを `docs/notes/rm084-refactorability-assessment.md` に追記予定。
    - 確認・共有方法（レビュー、ToDo 更新など）: Plan 承認内容を本 ToDo に転記し、実装後は該当テスト結果と差分要約を PR/ToDo へ記録。
    - 想定影響ファイル: `src/pptx_generator/pipeline/mapping.py`, 必要に応じて `src/pptx_generator/pipeline/__init__.py`, `tests/pipeline/` 配下のマッピング関連テスト、`docs/notes/rm084-refactorability-assessment.md`.
    - リスク: 状態集計の分解時にフォールバック・AI パッチ件数などの集計ロジックが変わる恐れ。例外処理パスを崩すと CLI/Pipeline の挙動に影響する。
    - テスト方針: `uv run --extra dev pytest tests/pipeline`（マッピング関連テスト中心）と必要に応じて CLI 統合テストを実行し、出力 JSON の互換性を確認する。
    - ロールバック方法: `mapping.py` の差分を revert すれば元の構成に戻せる。ドキュメント変更は同一コミットで巻き戻し可能。
    - 承認メッセージ ID／リンク: ユーザー返信「ok, 対応内容が全く違うため、新規にtodoファイルを作成して対応してほしい」（本会話 2025-11-30）。
- [ ] 設計・実装方針の確定
  - メモ: Plan 承認内容を踏まえた設計・実装方針をここに記載し、ユーザー確認が必要な論点があれば列挙する。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [ ] 実装
  - メモ: 
- [ ] テスト・検証
  - メモ: 
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
-
