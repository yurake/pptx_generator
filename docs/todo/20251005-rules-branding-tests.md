---
目的: 設定ファイルのローディングに対するユニットテストを整備し、破壊的変更を早期検知する
担当者: Codex
関連ブランチ: docs/todo-rules-branding-tests
期限: 2025-10-12
関連Issue: 未設定
---

- [ ] ブランチを作成し、正式ブランチ名の計画を固める
  - メモ: ToDo 先行。作成後は `feat/2-rules-branding-tests` へ切り替える
- [ ] `RulesConfig.load` の正常系と境界値テストを追加する
  - メモ: デフォルト値と `forbidden_words` の統合を確認
- [ ] `RulesConfig.load` の異常系テストを追加する
  - メモ: JSON 欠損・型不正を `pytest.raises` で検証
- [ ] `BrandingConfig.load` の正常系とフォールバックテストを追加する
  - メモ: `fonts.body` 未設定時に既定値へフォールバックすることを検証
- [ ] `BrandingConfig.load` の異常系テストを追加する
  - メモ: カラーコード不正などの例外ハンドリングを確認
- [ ] 新設テストを `uv run --extra dev pytest tests/test_settings.py` で実行し結果を記録する
- [ ] Issue 作成
  - メモ: Issue を作成したら番号と URL を記入する
- [ ] PR 作成
  - メモ: PR を作成したら番号と URL を記入する

## メモ
- ブランチパターン: ToDo 先行。暫定ブランチ `docs/todo-rules-branding-tests` で開始し、Issue #2 と連携後に正式ブランチへ切り替える。
- 設定ファイル: `config/rules.json`, `config/branding.json` をモックファイルで覆う必要あり。
