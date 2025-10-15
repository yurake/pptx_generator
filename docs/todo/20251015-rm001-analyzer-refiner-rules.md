---
目的: Analyzer / Refiner のルール拡張を実装し RM-001 の要件を満たす
関連ブランチ: feat/rm001-analyzer-refiner-rules
関連Issue: #185
roadmap_item: RM-001 Analyzer / Refiner ルール拡張
---

- [x] Plan 承認取得
  - メモ: 承認済み（2025-10-15）
- [x] 現行 Analyzer / Refiner ルールの仕様調査
  - メモ: 既存テスト・設定とロードマップの要件を再確認
- [x] ルール拡張の実装
  - メモ: `config/rules.json`、CLI、Refiner/Analyzer のオプション注入を更新
- [x] テスト追加・更新
  - メモ: `tests/test_settings.py` と `tests/test_refiner.py` を拡張し、`uv run --extra dev pytest` を完走
- [x] ドキュメント更新
  - メモ: `docs/policies/config-and-templates.md` に新セクションを追記
- [ ] PR 作成
  - メモ: PR 作成後に番号と URL を追記

## メモ
- 既存テンプレートやサンプルへの影響を確認すること。
