# PDF 自動生成 リハーサル実行ログ

## 目的
- LibreOffice 実環境で `pptx gen --export-pdf` を実行し、生成物と QA チェックリストを検証する。

## 前提条件
- Mac / Windows / Linux いずれかで LibreOffice 7.6 以降がインストール済み。
- `soffice` コマンドが PATH から呼び出せるか、または `LIBREOFFICE_PATH` でフルパスを指定。
- 工程4（`pptx compose` もしくは `pptx mapping`）で `.pptx/gen/generate_ready.json` が生成済み。サンプルワークフローは以下の通り。

  ```bash
  uv run pptx content samples/json/sample_jobspec.json \
    --content-source samples/contents/sample_import_content.txt \
    --output .pptx/content

  uv run pptx compose samples/json/sample_jobspec.json \
    --content-approved .pptx/content/content_approved.json \
    --draft-output .pptx/draft \
    --output .pptx/gen \
    --template samples/templates/templates.pptx
  ```
- ブランド設定は既定の `config/branding.json` を利用。

## 手順
1. 仮想環境をアクティブ化し、`uv sync` で依存をインストール。
2. 以下コマンドを実行。
   ```bash
   uv run pptx gen .pptx/gen/generate_ready.json \
     --branding config/branding.json \
     --export-pdf \
     --output .pptx/gen/rehearsal
   ```
3. 生成物を確認。
   - `proposal.pptx`
   - `proposal.pdf`
   - `analysis.json`
   - `audit_log.json`
4. [PDF 出力 QA チェックリスト](pdf-export-checklist.md) に沿って内容を検証。
5. 監査ログを開き、`pdf_export_metadata` の `attempts` / `elapsed_sec` が記録されていることを確認。
6. サポート運用ドキュメントに従い、失敗時の対応手順を試行。

## ステータス
- 2025-10-05: 開発環境（LibreOffice 未導入）では `PPTXGEN_SKIP_PDF_CONVERT=1` によるフォールバックを確認。
- 2025-10-06 (午前): 開発端末で `uv run pptx gen .pptx/gen/generate_ready.json --export-pdf --output .pptx/gen/rehearsal` を実行したが、`soffice` が検出できず Exit Code 5（LibreOffice 不足）で失敗。
- 2025-10-06 (午後): ユーザー端末で同コマンドを実行し、`proposal.pptx` / `proposal.pdf` / `analysis.json` / `audit_log.json` の生成を確認。`audit_log.json` の `pdf_export` には `attempts: 1`, `converter: libreoffice`, `elapsed_sec: 6.43s` が記録された。
- 2025-10-06 (夕方): `--libreoffice-path /Applications/LibreOffice.app/Contents/MacOS/soffice` を指定して同コマンドを再実行し、当環境でも PPTX / PDF / analysis / audit の各成果物を生成できることを確認。`audit_log.json` の `pdf_export` には `attempts: 1`, `converter: libreoffice`, `elapsed_sec: ~9.3s` が記録された。
- 2025-10-06: 自動化環境では依然として `soffice` が見つからないため、CI では `PPTXGEN_SKIP_PDF_CONVERT=1` を用いる想定。営業チーム端末での追加リハーサルは継続検討。
- 2025-11-03 (夕方): 開発端末 (LibreOffice 24.2.3.2) で `uv run pptx gen .pptx/gen/generate_ready.json --branding config/branding.json --export-pdf --output .pptx/gen/rehearsal` を再実行し、`proposal.pdf` を含む成果物一式と `audit_log.json.pdf_export.status=success` を確認。

## 次のアクション
- LibreOffice 実機でのリハーサル後、結果とスクリーンショットを本ドキュメントに追記。
- フォント埋め込み結果を QA チェックリストに記録し、差異があればテンプレート調整を検討。
