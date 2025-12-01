---
目的: RM-084 CLI/Pipeline リファクタビリティ向上 - 大規模モジュールの再分割（DraftStructuring / Mapping / LayoutValidation / Static Prepare）
関連ブランチ: chore/rm084-cli-refactorability
関連Issue: #359
roadmap_item: RM-084 CLI/Pipeline リファクタビリティ向上
---

- [x] ブランチ作成・初期コミット・push
  - メモ: 既存ブランチ `chore/rm084-cli-refactorability` を継続利用。ローカルはクリーンで push 済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 以下の方針で段階的に分割する。
    - 対象整理: `draft_structuring.py`, `mapping.py`, `layout_validation/suite.py`, `prepare_ai/orchestrator.py` の 4 ファイル。既存の RM-084 タスクでリファクタ済み領域と重複しないよう、サブパッケージ化と責務再配分に限定。
    - スコープ: 各モジュールのワークアイテム・アキュムレータ・出力処理を専用クラス／モジュールへ分離し、オーケストレーション層は公開 API を維持する。
    - 前提: 既存の JSON 出力・例外・CLI/Pipeline インターフェースを保ち、テストで互換性を保証する。
    - テスト方針: モジュール単位テストに加え `tests/cli/test_cli_generate_pipeline_flow.py` 等を再実行。
    - ロールバック: 各段階を独立コミット化して revert 容易性を確保。
  - [x] 設計・実装方針の共有場所を決定する（例: `docs/notes/rm084-refactorability-assessment.md` 追記）
    - メモ: 同ノートの「2025-12-02 Pipeline 大規模モジュール再分割計画」節に整理。
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [ ] 実装
  - メモ: 第1段階として `draft_structuring` をパッケージ化し、`types.py` / `dynamic_flow.py` へ分割。`DraftStructuringStep` は `build_dynamic_document` を利用する構成へ変更済み。以降は mapping → layout_validation → prepare_ai の順で進める。
- [ ] テスト・検証
  - メモ: 対象モジュールのユニット／統合テスト（CLI flow 含む）を網羅的に再実行する。
- [ ] ドキュメント更新
  - メモ: 設計メモ等への追記や更新不要の確認結果を記録する。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: `todo-sync` 実行後に自動付与される Issue 番号を記録する。
- [ ] チェックリスト整合確認
  - メモ: 子タスクの完了に応じて親タスクの状態も更新する。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録し、todo-auto-complete による自動更新結果を確認する。

## メモ
- 対象: `src/pptx_generator/pipeline/draft_structuring.py`, `src/pptx_generator/pipeline/mapping.py`, `src/pptx_generator/layout_validation/suite.py`, `src/pptx_generator/prepare_ai/orchestrator.py`
- 目的: 各ファイル 1,000 行超の状態を是正し、責務単位でモジュール／クラスへ再分割する。
- 先行タスクとの整合: 既存の RM-084 ToDo で CLI/Static まわりを段階的に改善済み。本タスクでは残存する大規模モジュールへ追加のリファクタを適用する。
- 現状把握（2025-12-02）:
  - DraftStructuring: DraftWorkItem / DraftAccumulator は導入済みだが、`DraftStructuringStep` がファイル書き出し・静的モード・AI 統計集計を同クラス内で保持している。`DraftStore` 依存や `SlideIdAligner` 等の外部ヘルパーが散在。
  - Mapping: `MappingWorkItem` / `MappingAccumulator` を使いながらも `_process_work_item` がテンプレ配列生成・fallback 判定・ログ生成を兼務。`table_anchor` 系ユーティリティなど他モジュールとの依存が肥大化。
  - LayoutValidation: `_build_layout_records` がプレースホルダー解析から AI 呼出・warning 集計まで一括管理。`TemplateBlueprint` 参照と `usage_tags` 正規化が絡む。
  - Prepare Static: `_build_cards_static` が章割当→プロンプト処理→LLM 応答検証を単一メソッドで保持。Blueprint slot 充足チェックや `resolve_table_anchor` との連携が複雑。
