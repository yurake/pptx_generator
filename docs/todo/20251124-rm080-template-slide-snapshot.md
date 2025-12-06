---
目的: RM-080 テンプレ実スライドスナップショット強化
関連ブランチ: feat/rm080-template-slide-snapshot
関連Issue: #319
roadmap_item: RM-080 テンプレ実スライドスナップショット強化
---

- [x] ブランチ作成・初期コミット・push
  - メモ: feat/rm080-template-slide-snapshot を作成し push 済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認メッセージ: 今スレッド OK。参照: docs/policies/context-engineering.md, CONTRIBUTING.md, docs/policies/task-management.md, docs/design/stages/stage-01-template.md。
    - 対象整理（スコープ、対象ファイル、前提）: `slide_snapshot.json` が TemplateExtractor の図形情報と突合できるよう、`SlideSnapshot` 系 dataclass と CLI (`src/pptx_generator/cli_handlers/template_extraction.py`, `src/pptx_generator/pipeline/analyzer.py`) を拡張する。既存 CLI オプションや Analyzer 連携は維持前提。
    - ドキュメント／コード修正方針: `ParagraphSnapshot`, `ShapeSnapshot`, `SlideSnapshot` へ段落属性（フォント名・太字/斜体・整列・行間・インデント等）と図形属性（z-order, 回転角, placeholder タグなど）を追加し `_serialize_slide_snapshot` で JSON へ反映。python-pptx から取得できない場合は `None` で明示し、ユーティリティ関数で値を正規化する。仕様差分は docs/design/cli/cli-command-reference.md と docs/design/stages/stage-01-template.md に記載。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo 更新と PR 説明で共有。`uv run --extra dev pytest tests/integration/test_cli_generate_pipeline_flow.py` ログを添付。
    - 想定影響ファイル: `src/pptx_generator/pipeline/analyzer.py`, `src/pptx_generator/cli_handlers/template_extraction.py`, `tests/integration/test_cli_generate_pipeline_flow.py`, 関連ドキュメント。
    - リスク: JSON サイズ増大による diff 可読性低下、python-pptx 属性未対応による例外。未知属性は `None` を許容し後方互換を確保する。
    - テスト方針: `uv run --extra dev pytest tests/integration/test_cli_generate_pipeline_flow.py` を中心に CLI 実行テスト。必要なら追加の単体テストを作成。
    - ロールバック方法: dataclass 拡張と `_serialize_slide_snapshot` 変更を revert し、既存項目のみ出力する状態へ戻す。
- [ ] 設計・実装方針の確定
  - メモ: SlideSnapshot 拡張（段落属性・図形メタ）と TemplateExtractor 連携で進める。
- [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
- [x] ドキュメント更新（要件・設計）
  - メモ: `docs/requirements/stages/stage-01-template.md` と `docs/design/stages/stage-01-template.md` を更新し、slide_snapshot.json の目的・内容を追記済み。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: SlideSnapshot データクラスと `_serialize_slide_snapshot` を拡張し、図形/段落属性を JSON 出力。Analyzer snapshot 生成側も同じ情報を含むよう更新。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/integration/test_cli_generate_pipeline_flow.py::test_cli_template_emits_slide_snapshot`
- [x] ドキュメント更新
  - メモ: 
  - [ ] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [ ] チェックリスト整合確認
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
