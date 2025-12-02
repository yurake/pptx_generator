---
目的: RM-084 CLI/Pipeline リファクタビリティ向上 - CLI 設定モジュールの分割と共通ヘルパー整備
関連ブランチ: chore/rm084-cli-refactorability
関連Issue: #359
roadmap_item: RM-084 CLI/Pipeline リファクタビリティ向上
---

- [x] ブランチ作成・初期コミット・push
  - メモ: `chore/rm084-cli-refactorability` を継続利用。push は DNS 復旧後に再実行予定。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: CLI 各ステップ（template / prepare / compose / gen）に影響する設定群を `settings/` 配下の責務別モジュールへ再配置し、共通 coercer・ローダーを整備する。
  - [x] 設計メモの参照・必要な追記箇所の確認
- [ ] 実装
  - [ ] 共通型変換ヘルパー（coerce_*）のモジュール化
  - [ ] CLI ステップ固有設定のサブモジュール化と `settings/__init__.py` の再エクスポート整備
  - [ ] 設定読み込み処理の lazy 化／DI 検討
  - [ ] テスト追加（設定バリデーション・読み込みユニットテスト）
- [ ] テスト・検証
  - メモ: `uv run --extra dev pytest tests/settings/test_settings_coercers.py`（新設）、`uv run --extra dev pytest tests/cli/test_cli_prepare_stage_flow.py`、`uv run --extra dev pytest tests/integration/test_cli_generate_pipeline_flow.py` などを予定。
- [ ] ドキュメント更新
  - [ ] docs/design/ や CLI ガイドの設定項目リファレンスを確認し、構造変更がある場合は追記
- [ ] 関連Issue 行の更新
  - メモ: `#359`
- [ ] チェックリスト整合確認
- [ ] PR 作成
- [ ] 実装
  - [ ] 共通型変換ヘルパー（coerce_*）のモジュール化
  - [ ] CLI ステップ固有設定のサブモジュール化と `settings/__init__.py` の再エクスポート整備
  - [ ] 設定読み込み処理の lazy 化／DI 検討
  - [ ] テスト追加（設定バリデーション・読み込みユニットテスト）
- [ ] テスト・検証
  - メモ: `uv run --extra dev pytest tests/settings/test_settings_coercers.py`（新設）、`uv run --extra dev pytest tests/cli/test_cli_prepare_stage_flow.py`、`uv run --extra dev pytest tests/integration/test_cli_generate_pipeline_flow.py` などを予定。
- [ ] ドキュメント更新
  - [ ] docs/design/ や CLI ガイドの設定項目リファレンスを確認し、構造変更がある場合は追記
- [ ] 関連Issue 行の更新
  - メモ: `#359`
- [ ] チェックリスト整合確認
- [ ] PR 作成
