---
目的: Analyzer の構造スナップショットに図形段落テキストを含め、実スライドのオブジェクト情報を把握できるようにする
関連ブランチ: feat/rm061-usage-tags-governance
関連Issue: #287
roadmap_item: RM-061 usage_tags ガバナンス強化
---

- [x] ブランチ作成と初期コミット
  - メモ: 既存ブランチ `feat/rm061-usage-tags-governance` 上で対応開始
- [x] 計画策定（スコープ・前提の整理）
  - メモ: ユーザー確認済み Plan を反映
    - 対象整理（スコープ、対象ファイル、前提）: `src/pptx_generator/pipeline/analyzer.py` の `_export_snapshot_slide` で出力する構造スナップショットのみを対象。既存の Layout Validation が参照するキーは変えず、段落情報を追加する前提で作業。
    - ドキュメント／コード修正方針: Analyzer のスナップショットに `paragraphs` をシリアライズし、テストで検証。ドキュメント更新は不要。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo を更新し、PR 作成時に差分とテスト結果を共有。
    - 想定影響ファイル: `src/pptx_generator/pipeline/analyzer.py`, `tests/test_analyzer.py`。
    - リスク: スナップショット JSON 拡張による外部ツール連携への影響。社内利用のみと判断し、後方互換策は取らない。
    - テスト方針: `pytest tests/test_analyzer.py` を実行し、スナップショットの段落出力を確認。
    - ロールバック方法: `_export_snapshot_slide` から `paragraphs` のシリアライズを削除すれば従来挙動へ戻せる。
    - 承認メッセージ ID／リンク: ユーザー「resume」メッセージ
- [x] 設計・実装方針の確定
  - メモ: Analyzer スナップショットの段落出力追加のみを対象とし、既存インターフェースを維持する方針で合意済み。
- [x] ドキュメント更新（要件・設計）
  - メモ: 外部仕様への影響が無いため追加ドキュメントは不要（内部仕様は Plan で共有済み）。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: スナップショット出力に段落配列を追加し、テストで段落を検証できるよう更新。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_analyzer.py`
- [x] ドキュメント更新
  - メモ: 本タスクは Analyzer 内部出力のみの変更のため、既存ドキュメントとの差異なしを確認（追加更新不要）。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [x] PR 作成
  - メモ: PR #290 https://github.com/yurake/pptx_generator/pull/290（2025-11-16 完了）

## メモ
- 計画のみで完了する場合は、判断者・判断日と次アクション条件をここに記載する。
