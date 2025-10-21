---
目的: Analyzer 警告をマッピング工程へ連動させ、AI 補完とフォールバック制御の精度を高める
関連ブランチ: feat/rm031-analyzer-mapping
関連Issue: #224
roadmap_item: RM-031 Analyzer マッピング補完連動
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/rm031-analyzer-mapping を main から作成し、ToDo 追加の初期コミット (docs(todo): add RM-031 tracker) を実施。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 2025-10-21 ユーザー承認済み（RM-031 mapping_log 拡張計画）。
- [x] 設計・実装方針の確定
  - メモ: mapping_log に analyzer サマリを付加し、meta に件数集計を保持する方針を確定。SimpleAnalyzerStep で analysis.json 生成時に mapping_log.json を再読込して slide_id ごとに issues を集計し、再書き込みする。
- [x] ドキュメント更新（要件・設計）
  - メモ: stage-05 マッピング要件と設計ドキュメントに Analyzer 連携を追記。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: MappingLog モデルへ analyzer サマリ項目を追加し、SimpleAnalyzerStep が mapping_log.json を更新する実装を追加。
- [x] テスト・検証
  - メモ: `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/test_mapping_step.py tests/test_analyzer.py` を実行しパス確認。
- [x] ドキュメント更新
  - メモ: roadmap, schema, stage 設計を更新し、Analyzer 連携の進捗を反映。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: Issue 作成後に番号へ更新する
- [ ] PR 作成
  - メモ: PR 作成時に URL と todo-auto-complete の結果を記録する

## メモ
- 当面は Analyzer 出力との差分突合範囲を決定するため、既存ログ構造の調査が必要。
