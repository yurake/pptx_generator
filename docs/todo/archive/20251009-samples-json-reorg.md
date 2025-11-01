---
目的: サンプル JSON を整理し `samples/json/` 配下に再配置する
関連ブランチ: chore/samples-json-reorg
関連Issue: #131
roadmap_item: RM-002 エージェント運用ガイド整備
---

- [x] ブランチ作成
- [x] `sample_spec*.json` を `samples/json/` 配下へ移動
  - メモ: 2025-10-31 時点で `sample_spec*.json` シリーズは `sample_jobspec.json` へ統合・廃止済み
- [x] README と各種ガイドの参照パス更新
  - メモ: `samples/AGENTS.md`, `config/AGENTS.md`, `AGENTS.md` など
- [x] テスト・CLI コマンドを新パスに追随させる
  - メモ: `tests/test_cli_integration.py` とドキュメント記載コマンド
- [x] PR 作成
  - メモ: PR #133（feat/samples-expansion）でマージ済み

## メモ
- 再配置後は `.pptxgen/outputs/` など生成物パスが変わらないことを確認する。
- 旧パス利用が見つかった場合は追記し、必要なら追加タスク化する。
