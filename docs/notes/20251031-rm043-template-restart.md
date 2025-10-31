# 2025-10-31 RM-043 作業再開ログ

## 実施手順

1. `docs/todo/20251026-sample-template-expansion.md` を最新化し、関連ブランチを追記。
2. テンプレート構造検証:
   ```bash
   UV_CACHE_DIR=.uv-cache uv run pptx layout-validate \\
     --template samples/templates/templates.pptx \\
     --output .pptx/validation/rm043
   ```
   - `diagnostics.json` の `shape_extract_error` を確認し、抽出コード修正の対象を特定。
3. 抽出ロジック修正:
   - `src/pptx_generator/pipeline/template_extractor.py` で `shape.placeholder_format` 取得時の `ValueError` / `AttributeError` を握り潰すよう改修。
4. サンプル JSON 整備:
   - `samples/json/sample_spec.json` を 50 ページ構成へ拡張（Two Column Detail アジェンダ、KPI チャート追加など）。
   - `samples/json/sample_content_approved.json` / `sample_content_review_log.json` の `current-challenges` 参照を同期。
   - `samples/json/sample_layouts.jsonl` を最新の抽出結果で更新。
5. ドキュメント更新:
   - `docs/requirements/requirements.md`, `docs/design/design.md`, `docs/runbooks/release.md` に RM-043 の運用手順を追記。
6. CLI 実行と検証:
   ```bash
   UV_CACHE_DIR=.uv-cache uv run pptx gen samples/json/sample_spec.json \\
     --template samples/templates/templates.pptx \\
     --output .pptx/gen/rm043 \\
     --emit-structure-snapshot

   UV_CACHE_DIR=.uv-cache uv run --extra dev pytest \\
     tests/test_renderer.py tests/test_cli_integration.py
   ```
   - 生成物 `.pptx/gen/rm043` を確認し、構造スナップショット・監査ログを取得。

## メモ
- layout-validate の警告（`placeholder_unknown_type` など）はテンプレート側で矢印図形がプレースホルダー化されていないことが原因。テンプレ修正時に対応検討。
- CLI 実行時のモニタリング警告（11 slides）は既知仕様であり、Analyzer 設定の閾値見直しが別タスク。
