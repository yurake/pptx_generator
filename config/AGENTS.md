# config ディレクトリ向け作業指針

## ファイル概要
- `rules.json`: 文字数・段落レベル・禁止ワードなどの生成ルールを定義。

## 変更手順
1. 変更内容を `docs/todo/` の該当タスクに記録し、影響範囲を整理する。
2. `uv run pptx compose samples/extract/jobspec.json --output .pptx/compose` で `generate_ready.json` を用意し、`uv run pptx gen .pptx/compose/generate_ready.json --output .pptx/gen` などでテンプレート由来のスタイル（TemplateStyle）が意図通り反映されることを確認する。独自 JobSpec を利用する場合は `meta.template_path` / `meta.layouts_path` を事前に設定してから実行する。
3. 必要に応じて `docs/policies/config-and-templates.md` に理由・検証手順を追記する（特に `rules.json` やテンプレートを更新した場合は必須）。
4. 既存テンプレートとの整合性を保つため、`templates/` や `samples/` のファイルが更新不要かを確認し、必要なら `docs/design/initiatives/template-style-governance.md` をアップデートする。ブランドスタイルを共有したい場合は `pptx template` で出力される `.pptx/template/branding.json` を設計メモとして参照する。

## バリデーション
- `rules.json` の改訂で Analyzer の警告が変わる場合は `tests/test_analyzer.py` や `tests/test_refiner.py` を更新する。
- テンプレートのスタイル（フォントやカラー）を変更した際は、レンダリング結果と `analysis.json` のメタ情報に矛盾がないかを `.pptx/gen/` の成果物で確認する。

## レビュー時の確認ポイント
- 変更理由と影響範囲が ToDo や関連ドキュメントに記載されているか。
- 既存テストが更新されたか、またはテスト結果に影響がない根拠が説明されているか。
- 本番運用で使用される外部ツール（LibreOffice など）との互換性に問題がないか。
