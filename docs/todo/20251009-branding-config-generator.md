---
目的: PPTX テンプレートから branding.json を生成する仕組みの調査と対応方針を決定する
関連ブランチ: 未作成
関連Issue: #134
roadmap_item: RM-009 テンプレート設定自動生成
---

- [ ] まずはブランチ作成
  - メモ: 実装フェーズ開始時に `feat/branding-config-generator` を想定。現段階では調査のため未作成。
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
- [ ] PR 作成
  - メモ: PR を作成したら番号と URL を記入する

## メモ
- PowerPoint テンプレートのスタイル情報取得には python-pptx の制限があるため、必要に応じて補完ルールを設ける。
