---
目的: テンプレートリリース時の差分検出・品質指標・実行環境メタを統合し監査プロセスを強化する
関連ブランチ: feat/rm035-template-release-audit
関連Issue: 未作成
roadmap_item: RM-035 テンプレートリリース監査強化
---

- [x] ブランチ作成と初期コミット
  - メモ: 2025-10-23 `main` から `feat/rm035-template-release-audit` を作成。初期コミットは後続で作成予定（現状差分は計画のみ）。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 2025-10-23 ユーザー承認済（本スレッド）。
- [x] 設計・実装方針の確定
  - メモ: 2025-10-23 `docs/notes/20251023-rm035-template-release-audit-plan.md` に設計方針とテスト計画を整理済み。
- [ ] ドキュメント更新（要件・設計）
  - メモ: RM-021/027 の成果との差分を踏まえて要件・設計への反映内容を記録する。
  - [ ] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: CLI 拡張、監査ロジック、設定ファイル、ゴールデンサンプル自動化スクリプトを追加し、既存処理との互換性を確認する。
- [ ] テスト・検証
  - [x] Python 単体・統合テスト (`UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/test_template_release.py tests/test_template_release_metrics.py tests/test_cli_integration.py`)
  - [ ] LibreOffice / Polisher バージョン整合確認（現環境では `soffice` が未導入のため pending）
- [ ] ドキュメント更新
  - メモ: 結果をロードマップや runbook、運用ドキュメントへ反映し、バージョン固定戦略を明文化する。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: Issue 作成後にフロントマターの `関連Issue` を `#xxx` 形式へ更新する。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフロー未動作時は理由をメモする（手動チェック禁止）。

## メモ
- 2025-10-23: 計画承認済。Analyzer メトリクスとゴールデンサンプルフローを中心に差分を整備する。
