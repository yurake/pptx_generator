# レイアウト検証スイート初期実装メモ（RM-022）

- `uv run pptx layout-validate` でテンプレ構造の抽出・スキーマ検証・差分レポートを一括実行する CLI を追加。
- `layouts.jsonl` はテンプレ ID・レイアウト ID・プレースホルダー一覧・ヒント情報を JSON Lines で出力し、`jsonschema` で即時検証。
- `diagnostics.json` では未知 PH 種別・重複アンカー・抽出失敗などを警告 / エラーに分類し、処理時間と件数をメトリクス化。
- ベースライン指定時に `diff_report.json` を生成し、レイアウト追加・削除・プレースホルダー座標変更を追跡。初期版では bbox と type を監視対象に設定。
- `tests/test_layout_validation_suite.py` で CLI 正常系と差分検知を回帰テスト化。将来的にはゴールデン JSON を導入し、サンプル差分比較をメタ情報（ハッシュや件数）に統一する。
- 今後: `usage_tags` 推定の精緻化（面積・比率ベース）、`docs/design/schema/samples/` へのサンプル整備、CI ジョブ組み込みを ToDo / Roadmap に反映予定。
