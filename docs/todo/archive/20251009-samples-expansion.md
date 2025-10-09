---
目的: samples を拡充し、テンプレート準備時の参照用に最小構成・フル構成の仕様と補助ファイルを整備する
関連ブランチ: feat/samples-expansion
関連Issue: #129
roadmap_item: RM-002 エージェント運用ガイド整備
---

- [x] まずはブランチ作成
- [x] 最小構成サンプルの仕様とテンプレートを整理し、既存ファイルを必要に応じて更新する
  - メモ: `samples/json/sample_spec_minimal.json` を新設し、`uv run pptx-generator run samples/json/sample_spec_minimal.json --workdir .pptxgen/minimal` で生成を確認
- [x] フル構成サンプル（多レイアウト・画像・表・グラフ想定）の仕様とテンプレートを作成し、差分を反映する
  - メモ: `samples/json/sample_spec.json` を更新し、`samples/templates/templates.pptx` を追加
- [x] ドキュメントと README 類にサンプル利用ガイドを追記し、参照先を整理する
  - メモ: README, `samples/AGENTS.md`, `docs/policies/config-and-templates.md` を更新済み
- [x] PR 作成
  - メモ: PR #133（feat/samples-expansion）でマージ済み

## メモ
- サンプル間で共通利用するアセットの管理方針を決める（例: 画像・資料の使い分け）
- CLI 統合テストで追加ケースが必要か検討する
- 2025-10-09: `uv run --extra dev pytest tests/test_cli_integration.py` を実行し、5 ケース成功を確認
- 箇条書き (`SlideBullet`) の `anchor` 対応検討は [docs/todo/20251010-renderer-slidebullet-anchor.md](../20251010-renderer-slidebullet-anchor.md)（RM-007 SlideBullet アンカー拡張）で管理する
