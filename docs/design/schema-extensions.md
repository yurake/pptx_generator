# JSON スキーマ拡張メモ (2025-10-05)

## 目的
- PPTX 生成の表・グラフ対応に向けて、入力仕様に `tables` と `charts` を追加する。
- 今後のレンダリング / 診断ステップ拡張の前提を明確化する。

## 追加フィールド概要
- `slides[].tables`: テーブル構造を定義。
  - `columns`: 表ヘッダの文字列リスト。
  - `rows`: 行データ。セルは文字列または数値を許容。
  - `style`: `header_fill` (任意), `zebra` (bool)。
- `slides[].charts`: グラフ構成を定義。
  - `type`: `column` などの文字列。描画実装時にサポート種別を定義。
  - `categories`: 軸ラベル。
  - `series`: シリーズごとの名前・値・色 (`color_hex`)。
  - `options`: `data_labels`、`y_axis_format` など追加設定。

## 実装ポイント
- `src/pptx_generator/models.py` にモデル (`SlideTable`, `SlideChart`, ほか) を追加。
- カラーフィールドは既存 `FontSpec` に倣って `#` 有無を統一整形。
- サンプル仕様 (`samples/json/sample_spec.json`) にテーブルとグラフの例を追加。
- 単体テスト (`tests/test_models.py`) で新フィールドが読み込めることを検証。

## 今後のタスク
- レンダラーでテーブル・グラフ描画を実装し、スタイル適用ルールを詰める。
- 診断ステップでテーブル/グラフの配置・サイズ・フォントを評価するロジックを検討。
- ドキュメント (README など) に新しい JSON 例を反映する。
