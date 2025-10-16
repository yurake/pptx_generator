---
目的: Analyzer テンプレの監査メトリクスを整備し、品質監視指標を定義する
関連ブランチ: feat/analyzer-template-audit-metrics
関連Issue: 未作成（確認後に更新）
roadmap_item: RM-027 Analyzer テンプレ監査メトリクス整備
---

- [x] ブランチ作成と初期コミット
  - 完了条件: `feat/analyzer-template-audit-metrics` ブランチを作成し初期コミットを記録する
  - メモ: `feat/analyzer-template-audit-metrics` を main から作成し、ToDo 追加を初期コミットへ含める予定
- [ ] 計画策定（スコープ・前提・担当の整理）
  - 完了条件: Approval-First 方針に沿った計画を作成し承認を得る
- [ ] 設計・実装方針の確定
  - 完了条件: 監査メトリクスの構成と採取方法を定義し関係者合意を得る
- [ ] 実装
  - 完了条件: 定義したメトリクスの収集・出力に必要なコードと設定を反映する
- [ ] テスト・検証
  - 完了条件: `uv run --extra dev pytest` などで関連テストを実行し結果を記録する
- [ ] 関連Issueの更新
  - 完了条件: フロントマターと Issue トラッカーの情報を最新化する
- [ ] PR 作成
  - 完了条件: テンプレートに沿った PR を作成しリンクを記録する

## メモ
- Approval-First の計画承認後に作業を開始する
