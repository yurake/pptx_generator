---
目的: PPTX テンプレートから branding.json を生成する仕組みの調査と対応方針を決定する
関連ブランチ: 未作成
関連Issue: #134
roadmap_item: RM-009 テンプレート設定自動生成
---

- [x] まずはブランチ作成
  - メモ: 既存ブランチ `feat/cli-toolkit-refactor` を流用して実装（2025-10-11）。
- [x] テンプレート構造と branding.json の対応関係を整理
  - メモ: `docs/notes/20251011-branding-config-mapping.md` に項目別マッピングと抽出手順を記録（2025-10-11）。
- [x] CLI / スクリプト化の選択肢と実装規模を評価
  - メモ: 同メモで Option A/B/C の比較と概算工数を整理（2025-10-11）。
- [x] PoC スクリプトでテンプレートからの抽出手順を検証
  - メモ: `scripts/branding_extract.py` 追加。`uv run python scripts/branding_extract.py --template samples/templates/templates.pptx` で JSON 出力を確認（2025-10-11）。
- [x] CLI へ抽出機能を統合し、テンプレート指定時のブランド切り替えに対応
  - メモ: `pptx gen` でテンプレート指定時に自動抽出。`tpl-extract` は `branding.json` を同時出力（2025-10-11）。
- [x] CLI 出力先オプションの整理とデフォルトディレクトリ更新
  - メモ: `pptx gen`/`tpl-extract` を `--output` で統一し、既定を `.pptx/gen` / `.pptx/extract` へ変更（2025-10-11）。
- [x] ブランド抽出失敗時のフォールバック挙動テストを追加
  - メモ: `tests/test_cli_integration.py::test_cli_gen_template_branding_fallback` を追加し、抽出エラー時にデフォルトへ切り替わることを確認（2025-10-11）。
- [x] `--output` 未指定時の既定ディレクトリを自動検証する統合テストを追加
  - メモ: `tests/test_cli_integration.py::test_cli_gen_default_output_directory` / `test_cli_tpl_extract_default_output_directory` を追加（2025-10-11）。
- [x] PR 作成
  - メモ: PR #170 https://github.com/yurake/pptx_generator/pull/170（2025-10-11 完了）

## メモ
- PowerPoint テンプレートのスタイル情報取得には python-pptx の制限があるため、必要に応じて補完ルールを設ける。
