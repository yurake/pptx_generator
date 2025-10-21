---
目的: Analyzer 警告をマッピング工程へ連動させ、AI 補完とフォールバック制御の精度を高める
関連ブランチ: feat/rm031-analyzer-mapping
関連Issue: 未作成
roadmap_item: RM-031 Analyzer マッピング補完連動
---

- [ ] ブランチ作成と初期コミット
  - メモ: feat/rm031-analyzer-mapping を main から作成済み。初期コミットは計画策定後に実施予定。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: ユーザー承認を得た計画内容を記録する
- [ ] 設計・実装方針の確定
  - メモ: Analyzer 警告データとマッピングログの突合方法を設計する
- [ ] ドキュメント更新（要件・設計）
  - メモ: 差分設計を docs/design/ へ反映するか判断する
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: `mapping_log.json` 拡張および CLI オプションの調整を想定
- [ ] テスト・検証
  - メモ: CLI 統合テストで Analyzer 連動の動作確認を行う
- [ ] ドキュメント更新
  - メモ: 実装結果を docs/notes/ などへ記録する
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: Issue 作成後に番号へ更新する
- [ ] PR 作成
  - メモ: PR 作成時に URL と todo-auto-complete の結果を記録する

## メモ
- 当面は Analyzer 出力との差分突合範囲を決定するため、既存ログ構造の調査が必要。
