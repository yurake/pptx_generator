---
目標: テキスト溢れ検知のログ可視化を行う
関連ブランチ: feat/overflow-logging
関連Issue: #538
roadmap_item: RM-000 例外: RMなし Issue #538
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ名: feat/overflow-logging / push 済み
    - 初期コミットは実装コミットで対応
- [x] 計画策定（スコープ・前提の整理）
  - メモ:
    - 対象スコープ: mapping_log に capacity_warnings を追加
    - 対象ファイル: src/pptx_generator/models/mapping.py, src/pptx_generator/models/__init__.py, src/pptx_generator/pipeline/mapping/processor.py, tests/pipeline/mapping/test_mapping_step_layout_assignment.py
    - 前提: mapping 段階では shape_id を取得できないため slide_id/element で記録
    - ドキュメント／コード修正方針: 既存 warnings を維持し、追加フィールドで拡張
    - 確認・共有方法: ToDo 更新、Issue #538
    - 想定影響ファイル: 上記
    - リスク: mapping_log のスキーマ追加による下流影響
    - テスト方針: PYTHONPATH=src python -m pytest tests/pipeline/mapping/test_mapping_step_layout_assignment.py
    - ロールバック方針: 追加フィールドと処理を revert
    - 承認メッセージ ID／リンク: ユーザー「反してなければ先進めていいよ」
- [x] 設計・実装方針の確定
  - メモ: capacity_warnings に slide_id/element/max_lines/actual_lines/layout_id を記録。既存 warnings は維持。
  - [x] 設計・実装方針メモの共有（必要なし）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: src/pptx_generator/models/mapping.py, src/pptx_generator/models/__init__.py, src/pptx_generator/pipeline/mapping/processor.py
- [x] テスト・検証
  - メモ: PYTHONPATH=src python -m pytest tests/pipeline/mapping/test_mapping_step_layout_assignment.py / 8 passed / coverage.xml / diff-cover: python -m diff_cover.diff_cover_tool coverage.xml --compare-branch origin/main（Coverage 100%, 12 lines）
- [x] ドキュメント更新
  - メモ: docs/todo 以外は変更不要
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合を確認）
  - [x] docs/design 配下（実装結果との整合を確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 関連Issue: #538
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない

## メモ
- 連続性メモ（短文化し、更新があれば上書きする）
  - 前提/制約: mapping 段階で shape_id は取得不可
  - 決定と理由: capacity_warnings 追加で溢れ位置を可視化
  - リスク(UNCONFIRMED): mapping_log のスキーマ追加による下流影響
  - Now/Next: Now=実装・テスト完了 / Next=コミット・PR
  - テスト実績/抜け: PYTHONPATH=src python -m pytest tests/pipeline/mapping/test_mapping_step_layout_assignment.py（8 passed, coverage.xml）/ diff-cover 100%（python -m diff_cover.diff_cover_tool coverage.xml --compare-branch origin/main）
- 計画のみで完了する場合は、判断者・判断日・次のアクション条件をここに記載する
