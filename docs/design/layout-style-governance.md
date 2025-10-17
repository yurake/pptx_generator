# レイアウトスタイル統一設計（RM-011）

## 目的
- PPTX 生成時にレイアウト単位でスタイル（フォント・配色・配置パターン）を制御し、ブランドの一貫性を担保する。
- `config/branding.json` を新スキーマへ刷新し、スタイル適用ロジックを設定駆動に切り替える。
- レイアウト／コンポーネントごとのスタイル変更をコード改修なしで反映できるようにする。

## スキーマ方針
### 全体構造
```jsonc
{
  "version": "layout-style-v1",
  "theme": {
    "fonts": { ... },
    "colors": { ... }
  },
  "components": {
    "table": { ... },
    "chart": { ... },
    "image": { ... },
    "textbox": { ... }
  },
  "layouts": {
    "<layout_name>": {
      "placements": {
        "<anchor_or_role>": { ... }
      }
    }
  }
}
```

### theme
- `fonts.heading` / `fonts.body`: 既定フォント。`bold` / `italic` などスタイル指定を追加可能な構造にする。
- `colors`: ブランド基調色。`primary` / `secondary` / `accent` / `background` を必須、`neutral` など拡張は任意。

### components
- **table**
  - `header`: `font` + `fill_color`.
  - `body`: `font` + `fill_color` + `zebra_fill_color`.
  - `border`: `color` / `width_pt`（任意）。
  - `padding_pt`: セル内余白。未指定時は既定値を利用。
- **chart**
  - `palette`: 系列の色配列（必須）。
  - `data_labels`: `enabled` / `format`.
  - `axis`: `font` + `color`.
- **image**
  - `fallback_box`: アンカー未指定時の配置（inch単位）。
  - `sizing`: 既定リサイズモード（`fit` / `fill` / `stretch`）。
- **textbox**
  - `fallback_box`: アンカー未指定時の配置。
  - `font`: 既定フォント（`theme.fonts.body` を上書き可）。
  - `paragraph`: 揃えや行間などの既定値。

### layouts
- レイアウト名（テンプレートの `layout`）をキーに、アンカー単位で個別スタイルを指定する。
- `placements` の `box`（座標）と `font` / `paragraph` / `fill_color` を指定可能。
- 役割名（例: `body`, `sidebar`, `metrics-table`）に紐付く設定を与え、テンプレート側の図形名と揃える。

## 実装影響
- `BrandingConfig` を再設計し、`theme` / `components` / `layouts` を dataclass へマッピングする。
  - 既存の `heading_font`, `body_font`, `primary_color` などは `theme` のショートカットとして保持。
  - 新スキーマ読み込み時のみ有効。旧構造はサポートしない。
- レンダラーの適用処理を設定駆動へ変更。
  - テーブル: `components.table` のスタイルを利用。
  - チャート: `components.chart.palette` を優先し、系列ごとの `color_hex` がない場合に使用。
  - 画像・テキストボックス: `components.image` / `components.textbox` の `fallback_box` を利用。
  - レイアウト固有設定（`layouts.*.placements`）がある場合はアンカー解決時に上書き。
- `pptx_generator/branding_extractor` は新スキーマへ対応させる（抽出結果を `theme` 相当へマッピング）。

## テスト計画
- `tests/test_settings.py`: 新スキーマ読み込みの正常系／異常系テストを更新。
- `tests/test_renderer.py`: テーブル配色・チャートパレット・フォールバック配置が設定通りになるよう期待値を刷新。
- `tests/test_cli_integration.py`: 新 `branding.json` へ差し替えた上で CLI 出力が成功することを確認。

## ドキュメント更新
- `config/branding.json` のサンプルを新スキーマに差し替え、`docs/policies/config-and-templates.md` に更新手順を追記する。
- `docs/requirements/requirements.md` / `docs/design/design.md` に「レイアウトスタイル設定を設定ファイルで制御する」旨を反映する。
- `docs/roadmap/roadmap.md` の RM-011 ステータスを「設計完了」へ更新予定。
- ToDo (`docs/todo/20251011-layout-style-governance.md`) に設計完了メモと次工程の記録を追加する。

## マイグレーション手順
1. `config/branding.json` を新スキーマへ置き換える。
2. CLI / テスト環境で `uv sync` 済みであることを確認してから `uv run --extra dev pytest` を実行。
3. 旧 `branding.json` を参照する資料・サンプルを全て更新し、新スキーマのみを利用するようにする。
4. テンプレ更新時は `layouts` セクションでアンカー別スタイルをメンテナンスし、`docs/notes/` に差分メモを残す。
