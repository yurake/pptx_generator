---
目的: prepare_card.json と compose 連携の本文保持整備（title/headline 要件とタイトルページ挙動の見直し）
関連ブランチ: feat/rm054-static-blueprint-plan
関連Issue: #297
roadmap_item: RM-054 静的テンプレ構成統合プランニング
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/rm054-static-blueprint-plan を main から作成済み（既存 RM-054 取り組みの継続ブランチ）。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: PrepareCard/ContentElements スキーマ刷新（title/headline XOR, subtitle 追加）、dynamic prepare でのタイトルページ制御、subtitle 伝播を compose/gen まで広げる。既存 `.pptx/prepare/prepare_card.json` スキーマ互換への影響を把握しつつ進める。
    - ドキュメント／コード修正方針: `src/pptx_generator/prepare/models.py`, `models.ContentElements`, `prepare_normalization`, `draft_structuring` を更新し、`docs/requirements/stages/stage-02-content-normalization.md` など要件・設計資料を同期。必要に応じ `docs/roadmap/roadmap.md`（RM-067 参照）へ注記を追加。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo 進捗に反映し、Plan 承認メッセージ（本スレッド）を PR/ToDo に明記。実装後は関連テスト結果と CLI 動作確認を共有。
    - 想定影響ファイル: `src/pptx_generator/prepare/models.py`, `prepare/orchestrator.py`, `prepare/prompts.py`, `pipeline/prepare_normalization.py`, `pipeline/draft_structuring.py`, `src/pptx_generator/models.py`, `tests/test_cli_prepare.py` 他 prepare/draft テスト、`docs/requirements`, `docs/design`。
    - リスク: モデル変更で既存成果物の読み込みが失敗する可能性。タイトルページ自動挿入により枚数変動が発生し、下流工程で意図しない挙動となる恐れ。Subtitle 追加がテンプレ依存 UI と矛盾するリスク。
    - テスト方針: `uv run --extra dev pytest tests/test_cli_prepare.py tests/test_cli_integration.py::test_prepare_dynamic` 等で prepare/draft フローを検証。必要に応じ CLI 手動実行で `.pptx/prepare/prepare_card.json` と `.pptx/compose/generate_ready.json` の挙動を確認。
    - ロールバック方法: 変更は機能単位でコミットし、問題発生時は該当コミットを revert する。スキーマ互換性問題が顕在化した場合は旧モデル定義へ戻す。
    - 承認メッセージ ID／リンク: （本スレッドの Plan 承認メッセージ）
- [ ] 設計・実装方針の確定
  - メモ: 2025-11-22 現在、subtitle の扱いとタイトルページ制御の最終仕様が未確定のため着手保留。RM-054 の静的 Blueprint 実装レビュー完了後（目安: 2025-11-25）に再検討する。
- [ ] ドキュメント更新（要件・設計）
  - メモ: スキーマ案が固まり次第、Stage-02 要件／設計を更新する。現時点では仕様整理待ちのため未着手。
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: 依存する設計が固まっていないため未着手。content elements のスキーマ変更と compose/draft の更新をまとめて行う予定。
- [ ] テスト・検証
  - メモ: 実装完了後に `uv run --extra dev pytest tests/test_cli_prepare.py tests/test_cli_integration.py::test_prepare_dynamic` を想定。現状はテスト対象が無く未実施。
- [ ] ドキュメント更新
  - メモ: 実装フェーズ後に roadmap／requirements／design／runbook／README を横断確認する。現時点では着手前。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
