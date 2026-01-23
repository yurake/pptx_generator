---
目的: 改行・空行の保持
roadmap_item: RM-098 改行・空行の保持
関連ブランチ: feat/rm098-linebreak-preservation
関連Issue: なし
期限:
---

# RM-098 改行・空行の保持

## 概要
改行・空行をPPTX出力で保持し、空行は点なしで表示する。

## タスク

### 計画フェーズ
- [x] ブランチ作成
  - ブランチ: `feat/rm098-linebreak-preservation`
- [x] Plan 作成と承認取得
  - 承認メッセージ ID: ユーザー「OK」

### 設計フェーズ
- [x] 方針整理
  - 空行は段落として保持し、空行の箇条書き記号を抑止する

### 実装フェーズ
- [x] 実装作業
  - `src/pptx_generator/generate_ready.py`
  - `src/pptx_generator/pipeline/renderer/bullets.py`
- [x] テスト追加・更新
  - `tests/generate_ready/test_generate_ready_utils.py`

### 検証フェーズ
- [x] テスト
  - `PYTHONPATH=src python -m pytest tests/generate_ready/test_generate_ready_utils.py`
  - 結果: 4 passed
  - coverage.xml: line-rate 4.999%（本テスト実行分）
  - diff-cover: 未実施（uv未導入）
- [x] 手動確認
  - `C:\PPT_test_rm098\20260103_総括\gen\proposal.pptx` を確認
  - 空行が点なしで表示されること

### ドキュメント更新
- [x] ロードマップ更新
  - `docs/roadmap/roadmap.md`
- [x] その他ドキュメント
  - 変更なし（対象外）

### レビュー・完了
- [x] PR 作成
  - PR: https://github.com/yurake/pptx_generator/pull/533
- [ ] マージ完了

## メモ

### 参照済みドキュメント
- `docs/policies/context-engineering.md`
- `CONTRIBUTING.md`
- `docs/policies/task-management.md`
