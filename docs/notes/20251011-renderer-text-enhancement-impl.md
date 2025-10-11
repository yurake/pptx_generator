# RM-012 レンダラーテキスト強化 実装メモ（2025-10-11）

## 目的
- `Slide.subtitle` / `Slide.notes` / `slides[].textboxes[]` をレンダラー経由で描画できるようにする。
- テキストボックスのレイアウト指定（アンカー／座標）と段落フォーマットを JSON 仕様へ反映する。

## 実施内容
- `SlideTextbox` を追加し、座標情報 (`position`) と段落設定 (`paragraph`) を Pydantic モデルで定義。
- SimpleRendererStep にサブタイトル、ノート、テキストボックス描画ロジックを追加し、ブランドフォント・段落設定を適用。
- テンプレートアンカー解決と座標フォールバックの両方に対応するヘルパを実装。
- サンプル仕様と設計ドキュメントを更新し、textboxes の利用例とアンカー運用を明文化。
- レンダラーテストに subtitle／notes／textboxes ケースを追加し、段落整形およびノート出力を検証。

## テスト
- `uv run --extra dev pytest tests/test_renderer.py`
- `uv run --extra dev pytest`
- `uv run pptx gen samples/json/sample_spec.json --workdir .pptxgen/outputs/anchor-check`
- `uv run python - <<'PY'`（Two Column Detail の `Body Right` / `Logo` アンカーへ textboxes を配置し、出力 PPTX の座標がテンプレートと一致することを確認）

## 未了事項・次ステップ
- テンプレート更新が必要な場合の追加検証（アンカー併用ケースのサンプル作成）を検討する。
