# 2025-10-23 RM-035 テンプレートリリース監査強化 設計メモ

## 目的
- リリース成果物に品質推移と実行環境情報を組み込み、監査観点の抜け漏れを防ぐ。
- ゴールデンサンプルの再実行と廃棄ポリシーを自動化・明文化し、テンプレ差分検証を再現性の高い手順へ整備する。

## 実装方針
1. **リリースメタのサマリ強化**
   - `TemplateRelease` に `summary` フィールドを追加し、レイアウト数・アンカー合計・プレースホルダー合計・警告/エラー件数・Analyzer issue/fix 件数を集計。
   - `TemplateReleaseReport` に現在値／ベースライン／差分のサマリを追加し、品質推移を JSON で可視化。
   - 既存 `layouts`・`diagnostics` 構造は維持しつつメタ情報を補足する。

2. **実行環境メタの取得**
   - Python / CLI / OS / LibreOffice / .NET (Polisher) のバージョン情報を収集し `TemplateRelease.environment` として記録。
   - LibreOffice / dotnet は存在しない環境でもエラーにせず `None` を記録し、警告を `diagnostics.warnings` に追記。
   - 取得処理は `template_audit/environment.py` に切り出し、テストでモック可能にする。

3. **ゴールデンサンプル再実行の自動化**
   - `--baseline-release` 指定時にゴールデンサンプル未指定なら、ベースラインの `golden_runs` に含まれる `spec_path` を再実行対象として自動追加。
   - ベースライン経由で spec を解決できなかった場合は警告を `diagnostics.warnings` に追加。
   - 自動追加分とユーザー指定分をユニーク化し、ゴールデン実行ログを従来通り保存。

4. **ドキュメント更新**
   - `docs/design/stages/stage-01-template-preparation.md` にサマリ計算と環境メタ格納手順を追記。
   - `docs/runbooks/release.md` へ LibreOffice / Polisher バージョン固定戦略とゴールデンサンプル廃棄ポリシーを追加。
   - `README.md` の `pptx tpl-release` セクションへ自動ゴールデンサンプル実行と新出力項目を記載。

## テスト計画
- 既存ユニットテスト (`tests/test_template_release.py`, `tests/test_template_release_metrics.py`) を更新し、新しい `summary`・`environment` フィールドと自動ゴールデン取得を検証。
- CLI 統合テスト (`tests/test_cli_integration.py`) にベースライン再実行ケースを追加し、`golden_runs.json` が自動生成されることを確認。
- 環境メタ収集はモックして deterministic に検証、LibreOffice 未インストール時の警告出力もテストする。

## リスク・フォローアップ
- dotnet / LibreOffice バージョン取得が遅延する可能性があるため、タイムアウトと警告抑制を実装する。
- JSON スキーマ追加に伴う後方互換性の確認が必要。サンプル JSON (`docs/design/schema/samples/`) も更新する。
- ゴールデンサンプル自動追加が大量 spec で時間を要するケースがあり得るため、将来的に明示的な制御フラグ（例: `--no-auto-golden`）を検討する。
