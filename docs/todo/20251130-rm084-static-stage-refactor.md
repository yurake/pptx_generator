---
目的: RM-084 CLI/Pipeline リファクタビリティ向上 - Prepare Static/Validation/API の責務分離
関連ブランチ: 未作成（Plan 承認後に chore/rm084-static-stage-refactor を作成予定）
関連Issue: #344
roadmap_item: RM-084 CLI/Pipeline リファクタビリティ向上
---

- [ ] ブランチ作成・初期コミット・push
  - メモ: Plan 承認後に `chore/rm084-static-stage-refactor` を main から作成し初期コミットを用意する。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan を転記する。
    - 対象整理（スコープ、対象ファイル、前提）: `src/pptx_generator/prepare_ai/orchestrator.py` `_build_cards_static`、`src/pptx_generator/layout_validation/suite.py` `_build_layout_records`、`src/pptx_generator/api/app.py` `create_app` を中心に、静的 Prepare／レイアウト検証／API の長大メソッドを役割ごとに分割し、既存ログ・例外・戻り値の互換性を保つ。設計メモ `docs/notes/rm084-refactorability-assessment.md` へ新構造を追記する。
    - ドキュメント／コード修正方針: 既存リファクタで導入したワークアイテム／アキュムレータのパターンを適用し、静的 Prepare は章割当→プロンプト生成→LLM 応答整形の三段構成、レイアウト検証はプレースホルダー収集→ヒューリスティック評価→AI 応答処理、API は router 切り出し＋依存プロバイダ共通化へ整理する。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo と PR で変更概要・テスト結果・リスクを共有し、必要に応じてログ抜粋を添付する。設計ノート更新を合わせてレビューに提示する。
    - 想定影響ファイル: `src/pptx_generator/prepare_ai/orchestrator.py`, `src/pptx_generator/layout_validation/suite.py`, `src/pptx_generator/api/app.py`, 関連テスト（`tests/prepare_ai/*`, `tests/layout_validation/*`, `tests/api/*`）、`docs/notes/rm084-refactorability-assessment.md`, `docs/todo/20251130-rm084-static-stage-refactor.md`。
    - リスク: LLM 応答整形やレイアウト診断ペイロードが変わることによる下流影響、FastAPI router 分割による依存注入の退行。既存テストでカバーされないケースに注意し、差分確認と手動検証を実施する。
    - テスト方針: `uv run --extra dev pytest tests/prepare_ai/test_prepare_ai_orchestrator_flow.py`、`uv run --extra dev pytest tests/layout_validation/test_layout_validation_suite_execution.py`、`uv run --extra dev pytest tests/api/test_draft_api_revision_flow.py` など対象モジュールのテストを重点実行し、最終的に `uv run --extra dev pytest` を一括実行する。
    - ロールバック方法: 各モジュールを個別コミットで管理し、問題発生時は該当コミットを revert して元の実装へ戻す。ドキュメント更新も同コミットで巻き戻す。
    - 承認メッセージ ID／リンク: ユーザー返信「ok」（本タスク Plan 承認）
- [ ] 設計・実装方針の確定
  - メモ: Plan 承認後に詳細方針を追記する。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [ ] 実装
  - メモ: 実装内容と未対応事項を記載する。
- [ ] テスト・検証
  - メモ: 実施テストと結果を記録する。
- [ ] ドキュメント更新
  - メモ: 変更点の影響を整理し、不要の場合も理由を記載する。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: Issue 番号更新は ToDo 完了時に再確認する。
- [ ] チェックリスト整合確認
  - メモ: 子タスク完了後に親タスクの状態を随時確認する。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録する。ワークフロー異常時のみ理由を残す。

## メモ
- 既存リファクタで得たワークアイテム／アキュムレータ構造を再利用し、静的 Prepare/Validation/API でも責務分割の一貫性を確保する想定。
