# config ディレクトリ向け作業指針

## ファイル概要
- `branding.json`: layout-style スキーマ（`version: "layout-style-v1"`）に従った参考設定。**Stage 4 以降はテンプレート内のスタイルを直接参照するため、`branding.json` は編集方針の共有やバックアップ用途に限定される。**
- `rules.json`: 文字数・段落レベル・禁止ワードなどの生成ルールを定義。

## 変更手順
1. 変更内容を `docs/todo/` の該当タスクに記録し、影響範囲を整理する。
2. `uv run pptx compose samples/extract/jobspec.json --output .pptx/compose` で `generate_ready.json` を用意し、`uv run pptx gen .pptx/compose/generate_ready.json --output .pptx/gen` などでテンプレート由来のスタイルが意図通り反映されることを確認する。独自 JobSpec を利用する場合は `meta.template_path` / `meta.layouts_path` を事前に設定してから実行する。
3. 必要に応じて `docs/policies/config-and-templates.md` に理由・検証手順を追記する（特に `components` や `layouts` を更新した場合は必須）。
4. 既存テンプレートとの整合性を保つため、`templates/` や `samples/` のファイルが更新不要かを確認し、必要なら `docs/design/initiatives/template-style-governance.md` をアップデートする。

## バリデーション
- サンプルの `config/branding.json` を編集する場合は `uv run python -m json.tool config/branding.json` などで JSON 形式を検証する。
- `rules.json` の改訂で Analyzer の警告が変わる場合は `tests/test_analyzer.py` や `tests/test_refiner.py` を更新する。
- テンプレートのスタイル（フォントやカラー）を変更した際は、レンダリング結果と `analysis.json` のメタ情報に矛盾がないかを `.pptx/gen/` の成果物で確認する。

## レビュー時の確認ポイント
- 変更理由と影響範囲が ToDo や関連ドキュメントに記載されているか。
- 既存テストが更新されたか、またはテスト結果に影響がない根拠が説明されているか。
- 本番運用で使用される外部ツール（LibreOffice など）との互換性に問題がないか。
