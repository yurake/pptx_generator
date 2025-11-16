---
目的: prepare_card.json のスキーマをゼロベースで再設計し、後続工程が扱いやすい構造へ刷新する
関連ブランチ: feat/rm054-static-blueprint-plan
関連Issue: #272
roadmap_item: RM-054 静的テンプレ構成統合
---

- [ ] ブランチ作成と初期コミット
  - メモ: 既存ブランチ feat/rm054-static-blueprint-plan 上で継続作業
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan（2025-11-16）
    - 対象整理（スコープ、対象ファイル、前提）: prepare_card.json の構造そのものを見直し、テンプレート非依存なスライド下書きとして再定義する。関連する読み込み処理（BriefNormalizationStepなど）とサンプルも整合させる。
    - ドキュメント／コード修正方針: スキーマ案に沿って `src/pptx_generator/brief` と `pipeline/brief_normalization.py`、および `samples/prepare/*.json` を刷新し、仕様ドキュメント（requirements/design）を更新する。
    - 確認・共有方法（レビュー、ToDo 更新など）: 本 ToDo で進捗管理し、スキーマ案・実装結果をユーザーと擦り合わせる。
    - 想定影響ファイル: `src/pptx_generator/brief/*.py`, `src/pptx_generator/pipeline/brief_normalization.py`, `tests/test_cli_prepare.py`, `samples/prepare/*.json`, `docs/requirements/stages/stage-02-content-normalization.md`, `docs/design/schema/stage-02-content-normalization.md`。
    - リスク: compose/mapping 等の後段工程が旧スキーマを前提としており、合わせて修正する必要がある。移行期間中の互換性は担保しない。
    - テスト方針: CLI prepare のモック／Azure 実行、関連 pytest を更新して実行する。
    - ロールバック方法: 新スキーマに起因する問題があれば該当変更を元に戻し、旧スキーマへ復元する。
    - 承認メッセージ ID／リンク: ユーザー承認 (「ok, 新規にtodoを作成して対応しよう」)
- [ ] 設計・実装方針の確定
  - メモ:
- [ ] ドキュメント更新（要件・設計）
  - メモ:
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ:
- [ ] テスト・検証
  - メモ:
- [ ] ドキュメント更新
  - メモ:
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ:
- [ ] PR 作成
  - メモ:

## メモ
