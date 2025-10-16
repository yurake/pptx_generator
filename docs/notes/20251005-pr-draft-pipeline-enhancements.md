# PR 下書き: パイプライン機能拡張（2025-10-05）

## 概要
- レンダラーをリファクタリングし、ブランド設定を直接参照しながら表・画像・グラフを描画できるようにした。
- `RenderingOptions` にフォールバック座標を持たせ、テンプレートなしでも安定したレイアウトを確保。
- サンプル仕様とアセットを拡充し、リッチコンテンツの想定ケースを再現。
- CLI 統合テストと新規レンダラーテストで描画・配色・データラベルを検証。

## 変更ファイル例
- `src/pptx_generator/pipeline/renderer.py`
- `src/pptx_generator/settings.py`
- `src/pptx_generator/cli.py`
- `samples/json/sample_spec.json`
- `tests/test_cli_integration.py`, `tests/test_renderer.py`
- `README.md`, `docs/todo/20251005-renderer-rich-content.md`

## テスト
```bash
uv run --extra dev pytest
uv run pptx gen samples/json/sample_spec.json --template samples/templates/templates.pptx
```

## 残課題
- 対応 ToDo の最終チェックと PR テンプレートへの反映。
- スクリーンショット（生成 PPTX 例）を取得して添付。
- `analysis.json` サンプル差し替え検討（必要なら別 PR）。
