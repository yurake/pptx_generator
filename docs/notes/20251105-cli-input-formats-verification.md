# CLI入力形式確認メモ（2025-11-05）

## 背景
- CLI で利用するプレペア入力の正式な対応形式について「JSON/JSONC/Markdown 以外（プレーンテキストや PDF）を受け付けるか」を確認するため調査を実施。

## 調査結果
- `src/pptx_generator/prepare/source.py:33-92` の `PrepareSourceDocument.parse_file` はファイルを UTF-8 テキストとして読み込み、拡張子が `.json` / `.jsonc` の場合のみ JSON 検証を行い、それ以外は Markdown としてパースする。
  - `.txt` 等のプレーンテキストは Markdown と同じフローで処理される。
  - PDF などバイナリ入力は UTF-8 デコード段階で例外となり、CLI 実行は失敗する。
- `src/pptx_generator/content_import/service.py:34-220` の `ContentImportService` ではファイル・URL・data URI の PDF/HTML/Text をテキスト化する多形式インポート処理が実装済み。
  - `.pdf` を指定した場合は LibreOffice 経由の変換を実行する。
  - HTTP/HTTPS や data URI も PDF/HTML/Text を検出しテキスト化する。
- 2025-12-03 更新: `pptx prepare` CLI が `ContentImportService` と統合され、PREPARE_PATH を複数（スペース/カンマ区切り）指定すると PDF・URL・data URI も自動テキスト化して取り込めるようになった。構造化ファイル（JSON/Markdown/TXT）は従来どおり `PrepareSourceDocument.parse_file` で読み込まれ、最終的に統合されたドキュメントが生成される。

## 結論
- CLI が正式にサポートする入力形式は JSON/JSONC/Markdown/TXT/PDF/URL/data URI。PDF や HTML は LibreOffice／HTML パーサを経由してテキスト化される。
- 取り込んだソースのメタ情報は `ai_generation_meta.json.import_sources` と `audit_log.json` に記録される。
