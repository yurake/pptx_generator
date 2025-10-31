# 2025-10-15 PPTX アナライザー刷新メモ

- 目的: RM-013 に沿って JSON ベースだった簡易診断を PPTX 実体解析へ置き換え、余白・グリッド・フォント・コントラストの診断精度を向上させる。
- 実装概要:
  - `SimpleAnalyzerStep` がレンダリング済み PPTX を `Presentation` として読み込み、図形 ID／アンカー名を手がかりに箇条書き・テキストボックス・画像を突合。
  - 図形位置（インチ）、サイズ、段落レベル、フォントサイズ／色を `ParagraphSnapshot` / `ShapeSnapshot` へ格納し、`analysis.json` に実体ベースのメトリクスを記録。
  - `grid_misaligned` 判定は 0.125in グリッドと許容 0.02in を基準とし、最寄りグリッド位置への移動提案を `fix.payload` に含める。
  - 画像余白 (`margin`) はスライド全体 (10.0in × 7.5in) を基準に算出し、上下左右いずれかの逸脱を報告。
- テスト:
  - `pytest tests/test_analyzer.py` で箇条書き・画像の検知内容が `analysis.json` に反映されることを確認。
  - `SimpleRendererStep` と組み合わせた統合フィクスチャで、`font_min`・`contrast_low`・`layout_consistency`・`grid_misaligned` の同時検知をカバー。
  - `uv run --extra dev pytest` を実行し、86 件のテストがすべて成功（実行時間 2.42s）。CLI 統合テストでは `samples/json/sample_jobspec.json` 起点の PPTX 生成フローとアナライザー処理が通過することを確認。
- 影響範囲:
  - レンダラーが画像／テキストボックスへ ID 名を再設定し、解析側で図形特定が可能になった。
  - `docs/requirements/requirements.md` と `docs/design/design.md` に PPTX 実体解析前提と新しい診断メトリクスを追記。
  - `tests/test_analyzer.py` を PPTX 実体ベースへ移行し、ダミー画像を用意して回帰主要ケースを固定。
- 未決事項・フォローアップ:
  - 大規模スライドでの性能計測と、`analysis.json` メトリクスのサマリ項目（平均フォントサイズなど）拡張は別途検討。
  - Refiner への自動修正適用範囲（フォント引き上げ・色補正）の拡大、および CLI 統合テストの更新を次フェーズで行う。
