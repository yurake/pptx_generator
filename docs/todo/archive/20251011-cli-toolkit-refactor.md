---
目的: CLI を再編し、テンプレート抽出やサンプル仕様生成など支援系機能を統合しやすい構成にする
関連ブランチ: feat/cli-toolkit-refactor
関連Issue: #158
roadmap_item: RM-019 CLI ツールチェーン整備
---

- [x] ブランチ作成
  - メモ: 2025-10-11 `feat/cli-toolkit-refactor` を作成済み
- [x] CLI エントリーポイントのリネーム方針を整理しドキュメントへ反映
  - メモ: README / AGENTS 系ドキュメント更新（2025-10-11）
- [x] コマンド名を `pptx gen` / `pptx tpl-extract` へ変更しテストを更新
  - メモ: `tests/test_cli_integration.py` など CLI 依存箇所を調整済み
- [x] 必要に応じてロードマップや関連ドキュメントを更新
  - メモ: `docs/roadmap/roadmap.md` に RM-019 を追記（2025-10-11）
- [x] PR 作成
  - メモ: PR #156 https://github.com/yurake/pptx_generator/pull/156（2025-10-11 完了）

## メモ
- 後方互換不要のため既存コマンドは廃止して問題なし。
- 将来的に `sample_spec.json` 自動生成コマンドを追加する前提で CLI 命名・構成を決める。
