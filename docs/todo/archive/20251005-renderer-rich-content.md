---
目的: レンダラーで表・画像・グラフを描画しブランドスタイルに準拠した PPTX を生成する
担当者: Codex
関連ブランチ: feat/pipeline-enhancements
期限: 2025-10-18
関連Issue: #10
---

- [x] スライド要素の描画戦略を整理し、アンカー解決方針を決める
  - メモ: 2025-10-05 `docs/notes/renderer-rich-content.md` にアンカー解決ポリシーを記録
- [x] テンプレート有無での座標フォールバック値を定義する
  - メモ: 2025-10-05 `RenderingOptions.fallback_*` に Inches 基準のレイアウトボックスを設定
- [x] 画像描画処理を実装し、`SlideImage` のサイズ指定とブランド既定値を適用する
  - メモ: 2025-10-05 `_apply_images` / `_resize_picture` で sizing=`fit|fill|stretch` をサポート
- [x] 表描画処理を実装し、ヘッダー色やテキストスタイルをブランド設定から決定する
  - メモ: 2025-10-05 ヘッダーはブランドのプライマリカラー、ゼブラ行はセカンダリカラーで描画
- [x] グラフ描画処理を実装し、系列カラーとデータラベル設定を反映する
  - メモ: 2025-10-05 系列カラーは `ChartSeries.color_hex` 優先、未指定時はブランドカラーをローテーション
- [x] `RenderingOptions` を拡張し、`BrandingConfig` を直接参照できるようにする
  - メモ: 2025-10-05 ブランドフォントを `BrandingFont` として保持
- [x] ブランド設定由来のフォントをタイトル・本文・表・グラフに適用する
  - メモ: 2025-10-05 タイトルは heading フォント、本文要素は body フォントで描画
- [x] `SimpleRendererStep` をリファクタリングし、新要素の描画ヘルパを分離する
  - メモ: 2025-10-05 `_apply_tables` `_apply_images` `_apply_charts` を新設
- [x] サンプル仕様 (`samples/json/sample_spec.json`) を更新し、画像・表・グラフの組み合わせを追加する
  - メモ: 2025-10-05 `samples/assets/logo.png` を追加し、サンプルに画像要素を含めた
- [x] レンダラー単体テストを追加し、新機能の描画ロジックを検証する
  - メモ: 2025-10-05 `tests/test_renderer.py` でフォント・カラー・データラベルを検証
- [x] CLI 統合テストを拡張し、生成ファイルに画像・表・グラフが含まれるケースを追加する
  - メモ: 2025-10-05 `tests/test_cli_integration.py` に形状検証を追加
- [x] `docs/` 配下にレンダラー拡張の設計ノートとテスト結果を記録する
  - メモ: 2025-10-05 `docs/notes/renderer-rich-content.md` を作成
- [x] `uv run --extra dev pytest` を実行し、追加テストの結果を記録する
  - メモ: 2025-10-05 テストスイート全体を実行しパスを確認
- [x] Issue と PR の更新
  - メモ: 2025-10-06 #10 を更新し、PR #7 をマージ済み。スクリーンショットと検証ログを共有

## メモ
- `python-pptx` のグラフ描画 API 仕様を確認する資料を収集する
- サンプル画像は CC0 素材を利用する
