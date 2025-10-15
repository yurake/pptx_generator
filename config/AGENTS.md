# config ディレクトリ向け作業指針

## ファイル概要
- `branding.json`: layout-style スキーマ（`version: "layout-style-v1"`）でフォント・カラー・要素別スタイル・レイアウト個別設定を定義。テンプレート抽出とレンダラーが参照する。
- `rules.json`: 文字数・段落レベル・禁止ワードなどの生成ルールを定義。

## 変更手順
1. 変更内容を `docs/todo/` の該当タスクに記録し、影響範囲を整理する。
2. `uv run pptx gen samples/json/sample_spec.json --branding config/branding.json` などで出力を確認し、テーブル・チャート・テキストボックスのスタイルが意図通り反映されることを確認する。
3. 必要に応じて `docs/policies/config-and-templates.md` に理由・検証手順を追記する（特に `components` や `layouts` を更新した場合は必須）。
4. 既存テンプレートとの整合性を保つため、`templates/` や `samples/` のファイルが更新不要かを確認し、必要なら `docs/design/layout-style-governance.md` をアップデートする。

## バリデーション
- JSON 形式の整合性は `uv run python -m json.tool config/branding.json` などで確認できる。
- `rules.json` の改訂で Analyzer の警告が変わる場合は `tests/test_analyzer.py` や `tests/test_refiner.py` を更新する。
- ブランド設定を変更した際はレンダリング結果を確認し、`analysis.json` に記録されるメタ情報と矛盾がないかをチェックする。特に `components` のフォールバック位置を変更した場合は `.pptx/gen/` へ生成された PPTX を目視で確認する。

## レビュー時の確認ポイント
- 変更理由と影響範囲が ToDo や関連ドキュメントに記載されているか。
- 既存テストが更新されたか、またはテスト結果に影響がない根拠が説明されているか。
- 本番運用で使用される外部ツール（LibreOffice など）との互換性に問題がないか。
