---
目的: Analyzer / Refiner ルール拡張テーマの初期対応として layout_consistency 診断を追加する
関連ブランチ: feat/analyzer-layout-consistency
関連Issue: 未作成
---

- [x] ブランチ作成
- [x] layout_consistency ルール実装とテスト更新
  - メモ: Analyzer に layout_consistency ルールと bullet_reindent fix を追加し、単体テストで検証。
- [x] ドキュメント更新
  - メモ: roadmap/design/policies/todo README の更新、docs/notes に背景メモを追加。
- [x] Refiner 調整ログを audit_log.json に反映
  - メモ: CLI で `refiner_adjustments` を監査ログへ出力し、統合テストを更新。
- [x] contrast_low 判定の調整方針を確定し実装
  - メモ: フォントサイズ閾値を導入して 3.0:1 の基準を適用し、メトリクスへ `required_ratio` を記録。
- [x] PR 作成
  - メモ: PR を作成したら番号と URL を記入する

## メモ
- 参照: docs/roadmap/README.md#L33
- LibreOffice 依存変更なし。Analyzer 機能の Python 側に限定して実装する。
- テスト: `uv run --extra dev pytest tests/test_refiner.py tests/test_analyzer.py tests/test_cli_integration.py`
- SimpleRefinerStep を追加し、`refiner_adjustments` アーティファクトで調整ログを記録。
