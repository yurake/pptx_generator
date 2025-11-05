# CLI入力形式確認メモ（2025-11-05）

## 背景
- CLI で利用するブリーフ入力の正式な対応形式について「JSON/JSONC/Markdown 以外（プレーンテキストや PDF）を受け付けるか」を確認するため調査を実施。

## 調査結果
- `src/pptx_generator/brief/source.py:33-92` の `BriefSourceDocument.parse_file` はファイルを UTF-8 テキストとして読み込み、拡張子が `.json` / `.jsonc` の場合のみ JSON 検証を行い、それ以外は Markdown としてパースする。
  - `.txt` 等のプレーンテキストは Markdown と同じフローで処理される。
  - PDF などバイナリ入力は UTF-8 デコード段階で例外となり、CLI 実行は失敗する。
- `src/pptx_generator/content_import/service.py:34-220` の `ContentImportService` ではファイル・URL・data URI の PDF/HTML/Text をテキスト化する多形式インポート処理が実装済み。
  - `.pdf` を指定した場合は LibreOffice 経由の変換を実行する。
  - HTTP/HTTPS や data URI も PDF/HTML/Text を検出しテキスト化する。
- 現行の `pptx content` CLI は `BriefSourceDocument.parse_file` を直接利用しており、`ContentImportService` は結線されていないため PDF や URL を CLI から扱うことはできない。

## 結論
- CLI が正式にサポートする入力形式は JSON/JSONC/Markdown（プレーンテキスト含む）であり、PDF は未サポート。
- PDF や URL を扱うには `ContentImportService` を CLI へ統合する機能追加が必要。
