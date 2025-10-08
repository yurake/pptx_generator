# Analyzer / Refiner ルール拡張メモ（layout_consistency）

- 背景: docs/roadmap/README.md#L33 のテーマに沿って、箇条書きのレベルジャンプを検出したい。
- 方針: 隣接項目のレベル差を 1 以内に制限し、初回項目はレベル 0 を既定とする。逸脱時は `layout_consistency` issue として検出し、再インデント用 fix (`bullet_reindent`) を提示する。
- 実装: `SimpleAnalyzerStep` で bullet 列を走査し、許容レベル (`previous_applied_level + 1`、初回は 0) を超える場合に issue/fix を生成。
- 実装: SimpleRefinerStep を追加し、`bullet_reindent` を適用して `refiner_adjustments` を記録（2025-10-07）。
- 監査ログ: `audit_log.json` に `refiner_adjustments` を出力し、調整履歴を参照できるようにした（2025-10-07）。
