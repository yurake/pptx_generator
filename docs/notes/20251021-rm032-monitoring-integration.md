# 2025-10-21 RM-032 Monitoring 統合メモ

## 背景
- RM-032 のゴールはレンダリング監査ログ (`rendering_log.json`) と Analyzer 出力を突合し、品質アラートを自動配信できる状態にすること。
- 既存フローでは Polisher / LibreOffice 実行後の Analyzer 再走が行われず、改善度メトリクスを計測できなかった。
- CI 連携や運用通知の起点となる成果物が不足しており、`audit_log.json` には監視サマリが存在しなかった。

## 方針
1. Renderer 直後のベースライン解析 `analysis_pre_polisher.json` を追加し、Polisher 適用後との差分を計測。
2. Polisher・LibreOffice 実行後に Analyzer を再度実行し、`analysis.json` を最新状態へ更新。
3. 新ステップ `MonitoringIntegrationStep` を導入し、`monitoring_report.json` と CLI / audit 用サマリ (`monitoring_summary`) を生成。
4. `audit_log.json` へ監視サマリを追記し、CI から `alert_level` / `headline` を読み取れるようにする。

## 監視レポート仕様
- `rendering.warnings_total` と `analyzer.after_pipeline.total` を主要指標として集計。
- Analyzer before/after の差分から `resolved`, `delta`, `resolved_issue_ids` を算出。
- `alerts`: スライド単位でレンダリング警告・Analyzer 課題を並記。優先度判定は `severity` に基づき `critical` / `warning` / `ok` を付与。
- `pipeline`: Polisher / PDF export のメタデータを転記し、外部ツールの失敗をアラートと紐付けられるようにした。

## 今後の検討事項
- Slack / Teams など通知チャネルへの直接連携（現状は JSON サマリのみ）。
- `monitoring_report.json` の差分比較を CI で自動化する仕組み。
- Analyzer issue の `severity` 拡張（`critical` 判定基準の明確化）。
- Polisher 再実行時のベースライン更新有無（複数回リトライ時のログ保持方法）。
