# Issue #8: PDF 自動生成対応

## 背景
- LLM 生成の PPTX を即座に配布可能な PDF に変換するニーズが営業チームから挙がった。
- LibreOffice を利用した自動変換パイプラインを実装し、配布準備時間を短縮することが目的。

## スコープ
- CLI への `--export-pdf` オプション追加とユーザー向け UX 整理。
- LibreOffice 変換ステップのリトライ・タイムアウト制御、PPTX 保存モード切替。
- CI/テスト環境で LibreOffice が無い場合のフォールバック設計。
- 監査ログ (`audit_log.json`) への変換メタ情報追加と QA チェックリスト整備。

## 完了条件
- CLI 経由で PDF が生成され、`outputs/custom.pdf` 等の命名切替が可能。
- `analysis.json` と同階層に `audit_log.json` が出力され、`pdf_export_metadata` が記録される。
- LibreOffice 未導入環境でも `PPTXGEN_SKIP_PDF_CONVERT=1` でジョブが成功する。
- QA チェックリストとサポート運用手順が docs 配下に整備される。
- テスト (`uv run --extra dev pytest`) がグリーンであること。

## リンク
- ToDo: [docs/todo/20251005-pdf-export-automation.md](../../todo/20251005-pdf-export-automation.md)
- ブランチ: `feat/pdf-export-automation`
- 参考資料: [docs/qa/pdf-export-checklist.md](../../qa/pdf-export-checklist.md)
