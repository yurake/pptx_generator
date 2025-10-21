---
目的: Analyzer と監査ログを突合し、品質アラート自動化の仕組みを整備する
関連ブランチ: feat/rm-032-monitoring
関連Issue: #225
roadmap_item: RM-032 Analyzer レンダリング監視統合
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/rm-032-monitoring を main から作成。初期コミットで ToDo を追加済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認取得済（2025-10-21）。
- [x] 設計・実装方針の確定
  - メモ: Analyzer と監査ログの突合方針を MonitoringIntegrationStep で統合。
- [x] ドキュメント更新（要件・設計）
  - メモ: docs/design/stages/stage-06-rendering.md、docs/design/schema/stage-06-rendering.md、docs/requirements/stages/stage-06-rendering.md を更新。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: MonitoringIntegrationStep を追加し、analysis_pre_polisher.json / monitoring_report.json を出力。
- [x] テスト・検証
  - メモ: `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/test_cli_integration.py` を実行し 26 件成功。通知 PoC は別途検討。
- [x] ドキュメント更新
  - メモ: docs/roadmap を更新済み。docs/runbook / README / AGENTS への追加要件は本スコープ外につき更新不要。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下（更新不要を確認）
  - [x] README.md / AGENTS.md（更新不要を確認）
- [ ] 関連Issue 行の更新
  - メモ: Issue 番号確定後に更新する。
- [ ] PR 作成
  - メモ: PR 作成時に todo-auto-complete の動作を確認する。

## メモ
- docs/notes/20251021-rm032-monitoring-integration.md に検討内容を整理済み。通知 PoC の要否は次フェーズで判断する。
