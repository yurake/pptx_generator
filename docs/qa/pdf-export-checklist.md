# PDF 出力 QA チェックリスト

- 実行コマンド:
  - `uv run pptx gen spec.json --export-pdf`
  - `uv run pptx gen spec.json --export-pdf --pdf-mode only`
- 期待アウトプット:
  - `outputs/proposal.pptx`（`--pdf-mode only` 時は未生成）
  - `outputs/proposal.pdf` または指定ファイル名
- 検証項目:
  - フォント埋め込み: PDF ビューアで `ファイル > プロパティ` を開き、ブランドフォントが埋め込まれていること。
  - ページ番号: スライド末尾まで連番が維持されていること。
  - 余白・レイアウト: PPTX 出力と比較し、余白崩れや画像の欠落がないこと。
  - 解析レポート: `analysis.json` が更新され、スライド数が一致していること。
  - リトライログ: LibreOffice エラー発生時は `logs/pdf_export_*.log`（未実装時は CLI 出力）を確認し、再実行後に成功すること。
  - 環境変数スキップ: `PPTXGEN_SKIP_PDF_CONVERT=1` で空の PDF が生成され、CI で失敗しないこと。
  - エラーハンドリング: `soffice` 非インストール環境で Exit Code 5 とメッセージが出力されること。

- レビュー手順:
 1. 上記チェックを実施し、不備があれば該当 ToDo に記録。
 2. 改善が必要な場合は `docs/todo/20251005-pdf-export-automation.md` に追記し、ステータスを更新。
 3. 完了後はチェックシートとログを添付して QA 室へ共有する。
