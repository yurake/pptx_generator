---
目的: RM-064 レイアウト候補メタ情報拡充 — レイアウト構造の記述文を生成し AI プロンプトへ活用する
関連ブランチ: feat/rm064-layout-ai-metadata
関連Issue: #281
roadmap_item: RM-064 レイアウト候補メタ情報拡充
---

- [x] ブランチ作成と初期コミット
  - メモ: 既存ブランチ `feat/rm064-layout-ai-metadata` 上で継続対応するため新規作成なし。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan
    - 対象整理（スコープ、対象ファイル、前提）: Stage1 でレイアウト構造を文章化するヘルパーを追加し、`LayoutInfo` → `layouts.jsonl.meta.layout_description` に反映。Stage2 (Template AI) / Stage3 (Layout AI・mapping ログ) のペイロードへ同フィールドを流し込む。
    - ドキュメント／コード修正方針: `template_extractor.py`・`layout_validation/suite.py`・`template_ai/service.py`・`draft_recommender.py`・`draft_structuring.py` を中心に更新し、`docs/design/schema/stage-02-template-structure-extraction.md` ほか設計ドキュメントとサンプル JSON を揃える。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo／チャットで進捗を共有し、必要に応じて `docs/notes` に補足メモを追加。
    - 想定影響ファイル: `src/pptx_generator/pipeline/template_extractor.py`, `src/pptx_generator/layout_validation/suite.py`, `src/pptx_generator/template_ai/service.py`, `src/pptx_generator/draft_recommender.py`, `src/pptx_generator/pipeline/draft_structuring.py`, `docs/design/schema/stage-02-template-structure-extraction.md`, サンプル JSON, 関連テスト。
    - リスク: 自動生成文の品質、AI プロンプト増加によるコスト、既存テストの期待値変更。
    - テスト方針: Stage1 ヘルパーの単体テスト、Template AI/Layot AI ペイロードへの組み込み確認、`draft_mapping_log.json` 出力の CLI テスト更新。
    - ロールバック方法: `layout_description` 生成ロジックを revert し、メタ拡張前の状態へ戻す。
    - 承認メッセージ ID／リンク: このチャット（2025-11-23 「okです」）
- [x] 設計・実装方針の確定
  - メモ: Stage1 で説明文を生成 → Stage2 で `layouts.jsonl.meta.layout_description` と Template AI ペイロードへ連携 → Stage3 の推薦・マッピングログで参照する三段構成で確定。
- [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - メモ: 本 ToDo に方針と対象ファイルを記録済み。追加ノート不要と判断。
- [ ] ドキュメント更新（要件・設計）
  - メモ: `layout_description` を要件・設計ドキュメントに追記する。
  - メモ: Stage1 Template の LLM 出力要件として layout_description を位置づけ、設計/要件ドキュメントへ明記する。
  - [x] docs/requirements 配下
    - メモ: `docs/requirements/stages/stage-01-template-pipeline.md` に layout_description 必須化を追記。
  - [x] docs/design 配下
    - メモ: `docs/design/schema/stage-02-template-structure-extraction.md` / `docs/design/stages/stage1-stage3-metadata-interface.md` へ説明文フィールドと LLM 要件を反映。
- [x] 実装
  - メモ: `utils/layout_metadata.py` に説明文ヘルパーを追加し、`template_extractor.py`・`layout_validation/suite.py`・`draft_recommender.py`・`draft_structuring.py`・`pipeline/mapping.py` で layout_description を連携。`MappingSlideMeta` / `MappingLogSlide` へ説明文を保持。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_layout_validation_suite.py tests/test_layout_recommender.py tests/test_draft_structuring_step.py` を実行し 15 件成功。
- [ ] ドキュメント更新
  - メモ: 対象ドキュメントの更新内容を記載。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: 必要に応じて Issue #281 の最新状況を反映する。
- [ ] チェックリスト整合確認
  - メモ: 子タスク完了状況を確認し、親タスクのチェック漏れがないようにする。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
