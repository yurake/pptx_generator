# PR: feat/pdf-export-automation

## 目的
- PDF 自動生成フローを実装し、`docs/todo/20251005-pdf-export-automation.md` に定義した各項目を完了させる。
- 監査ログと QA プロセスを整備して運用フェーズへ移行可能にする。

## 変更概要
1. `PdfExportStep` を追加し、LibreOffice 連携とスキップモードを実装。
2. CLI オプション (`--export-pdf`, `--pdf-mode`, `--pdf-output` 他) とエラーハンドリングを拡張。
3. `audit_log.json` 出力と `pdf_export_metadata` の記録を実装。
4. README / design / support / QA 文書を更新し、チェックリストを追加。
5. CLI 統合テストを増強し、PDF 生成・only モード・スキップ環境を検証。

## レビュー観点
- LibreOffice 実環境での挙動確認（別途リハーサル記録参照）。
- 監査ログのフォーマット妥当性とマスキング不要なデータのみが出力されているか。
- スキップ環境変数の利用が CI で問題にならないか。
- テスト実行時間への影響（現状 1.2s 追加）。

## TODO
- [x] LibreOffice 実環境での最終リハーサル結果を添付（2025-10-06 ユーザー端末で成功。ログ: `.pptxgen/rehearsal/outputs/audit_log.json`、詳細: [docs/qa/pdf-export-rehearsal.md](../../qa/pdf-export-rehearsal.md)）。`--libreoffice-path /Applications/LibreOffice.app/Contents/MacOS/soffice` 指定で当環境でも成功を確認。
- [x] レビュワー: 開発者本人がリハーサル・コードレビューを実施済み。
- [x] リリースノート草案を docs/roadmap に追記（2025-10-06 更新履歴を追加）。

## 添付
- QA: [docs/qa/pdf-export-checklist.md](../../qa/pdf-export-checklist.md)
- Support Runbook: [docs/runbooks/support.md](../../runbooks/support.md)
- Issue: [docs/notes/issues/0008-pdf-export-automation.md](../issues/0008-pdf-export-automation.md)
