# samples ディレクトリ向け作業指針

## 構成
- `sample_spec.json`: CLI 実行時の標準入力例。新しいフィールドを追加した場合はここにサンプル値を反映する。
- `assets/`: テストやドキュメントで利用する画像・グラフなどの補助ファイルを配置。
- `skeleton.pptx`: 提案書の初期テンプレート。変更時は `docs/policies/config-and-templates.md` の手順に従い検証する。

## 運用ルール
- サンプル JSON は公開前提のダミーデータを使用し、実案件情報を含めない。
- `sample_spec.json` を更新した際は `tests/test_cli_integration.py` の期待値や `docs/` の使い方ガイドを確認する。
- テンプレートを差し替える場合は `uv run pptx-generator run` で出力差分を確認し、`docs/runbooks/release.md` に影響がないか検討する。

## テスト連携
- CLI 統合テストで参照されるため、パスやスライド数の変更は `tests/test_cli_integration.py` のアサーションと合わせて更新する。
- `assets/` にファイルを追加した場合は、テストやドキュメントから相対パスで参照できるかを確認する。

## レビュー時の確認ポイント
- サンプルが最新スキーマに準拠し、未使用フィールドや古いキーが残っていないか。
- テンプレート更新に伴い、ブランドカラーやフォントの整合性が取れているか（必要なら `config/branding.json` と併せて変更）。
- ドキュメントや README のサンプルコマンドが最新のファイル構成を反映しているか。
