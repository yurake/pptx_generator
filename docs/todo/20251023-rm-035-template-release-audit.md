---
目的: テンプレートリリース時の差分検出・品質指標・実行環境メタを統合し監査プロセスを強化する
関連ブランチ: feat/rm035-template-release-audit
関連Issue: #233
roadmap_item: RM-035 テンプレートリリース監査強化
---

- [x] ブランチ作成と初期コミット
  - メモ: 2025-10-23 `main` から `feat/rm035-template-release-audit` を作成。初期コミットは後続で作成予定（現状差分は計画のみ）。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 2025-10-23 ユーザー承認済（本スレッド）。
- [x] 設計・実装方針の確定
  - メモ: 2025-10-23 `docs/notes/20251023-rm035-template-release-audit-plan.md` に設計方針とテスト計画を整理済み。
- [x] ドキュメント更新（要件・設計）
  - メモ: `docs/requirements/stages/stage-01-template-preparation.md` に summary/environment 要件を追記済み。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: CLI 拡張、監査ロジック、設定ファイル、ゴールデンサンプル自動化スクリプトを追加し、既存処理との互換性を確認する。
- [x] テスト・検証
  - [x] Python 単体・統合テスト (`UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/test_template_release.py tests/test_template_release_metrics.py tests/test_cli_integration.py`)
  - [x] LibreOffice / Polisher バージョン整合確認
    - メモ: 2025-10-25 LibreOffice 25.8.2.2 (`soffice --headless --version`) / dotnet SDK 9.0.306。`uv run pptx gen samples/json/sample_spec.json --template samples/templates/templates.pptx --export-pdf` で `proposal.pdf` を生成し、`.pptx/gen/audit_log.json` の `pdf_export.status` が `success` であること、Polisher の TargetFramework `net9.0` と SDK が一致することを確認。
- [x] ドキュメント更新
  - メモ: ロードマップ（Mermaid 依存更新・summary導入メモ）・要件・設計・runbook・README の整合を反映済み。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: Issue 作成後にフロントマターの `関連Issue` を `#xxx` 形式へ更新する。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフロー未動作時は理由をメモする（手動チェック禁止）。

## メモ
- 2025-10-23: 計画承認済。Analyzer メトリクスとゴールデンサンプルフローを中心に差分を整備する。
