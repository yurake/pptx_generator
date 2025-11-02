# 工程5 PPTX レンダリング 設計

## 目的
- `rendering_ready.json` とテンプレートを用いて最終 `output.pptx` を生成し、軽量整合チェックと監査ログを出力する。工程3/4の成果物は `rendering_ready` 内の `job_meta` / `job_auth` を通じて参照する。
- CLI では `uv run pptx render <rendering_ready.json>` で単体実行でき、`uv run pptx gen` は内部で `mapping` → `render` を順に呼び出す。
- LibreOffice PDF 変換や Open XML Polisher との統合を考慮した拡張性を持たせる。

## コンポーネント
| コンポーネント | 役割 | 技術 |
| --- | --- | --- |
| Rendering Orchestrator | スライド生成・PH 挿入・ノート/フッター設定 | Python (`python-pptx`) |
| Rendering Consistency | 空プレースホルダー検知、主要要素の有無確認、警告サマリ生成 | Python |
| Audit Logger | `rendering_log.json`, `audit_log.json` の生成 | Python |
| PDF Converter | LibreOffice headless で PDF 出力 | CLI (`soffice`) |
| Polisher Bridge | Open XML SDK プロジェクト呼び出し | .NET 8 CLI |

## フロー
1. Rendering Orchestrator がテンプレートを開き、`rendering_ready.json` から再構築した `JobSpec` を基にスライドを生成。  
2. 各 PH にテキスト・表・画像を挿入し、フォーマット調整。  
3. Pre-Analyzer がレンダリング直後の PPTX を解析し、ベースラインとして `analysis_pre_polisher.json` を生成。  
4. Rendering Consistency が空プレースホルダーやスライド数不一致をチェックし、検知結果を `rendering_log.json` に追記。  
5. 警告件数と代表メッセージを CLI INFO ログへ出力。  
6. 監査メタ (`audit_log.json`) と生成ログを保存。  
7. Polisher Bridge を起動して Open XML Polisher を実行（`polisher.enabled` または `--polisher` 指定時）。  
8. Polisher 実行後、必要に応じて整合チェックを再評価し、監査ログに結果を反映。  
9. `--export-pdf` 指定時は LibreOffice を呼び出し PDF を生成。  
10. Analyzer が Polisher / LibreOffice 適用後の PPTX を再解析し、`analysis.json` とスナップショットを出力。  
11. Monitoring Integration Step が `rendering_log.json` と Analyzer 出力（before/after）を突合し、`monitoring_report.json` とアラートサマリを生成。  

## ログ / 成果物
- `analysis_pre_polisher.json`: Renderer 出力直後の Analyzer 結果（課題ベースライン、Polisher 効果比較用）。  
- `rendering_log.json`: スライド毎の `layout_id`、主要要素の検出フラグ、警告一覧（`missing_title` / `empty_placeholder` など）、警告件数、`generated_at`、`rendering_time_ms`。
- `audit_log.json`: テンプレ版、生成物ハッシュ、`rendering_log.json` パス、整合チェックサマリ、`polisher` / `pdf_export` メタ（実行可否、ステータス、実行時間、リトライ回数）を保持。
- `monitoring_report.json`: レンダリング監査と Analyzer before/after の突合結果、改善度メトリクス、通知向けアラート一覧を保持。
- `stdout`: 主要な処理ステップと警告を INFO レベルで出力。Polisher 有効時は `Polisher: success` と JSON サマリを表示し、無効時は `Polisher: disabled` を表示。レンダリング監査の警告件数と `rendering_log.json` のパスを出力。

## エラーハンドリング
- 要素挿入失敗 → スライド番号と PH を特定してログ化、exit code 1。
- LibreOffice 失敗 → 再試行制御（最大 3 回）、それでも失敗なら `pdf_status=failed`。
- Polisher 失敗 → PPTX は保持しつつ警告を出力し、CLI は exit code 6 で異常終了。

## 設定項目
- `rendering.max_table_width_pt`, `rendering.bullet_line_spacing`, `rendering.default_note_template`
- `pdf.retry_limit`, `pdf.timeout_sec`
- `polisher.enabled`, `polisher.executable`, `polisher.rules_path`, `polisher.timeout_sec`, `polisher.arguments`
- `config/polisher-rules.json`: Polisher 用のルールファイル（フォントサイズ・色などフォールバック向け設定）を JSON で定義。段落インデントやブランド既定の行間は Renderer が適用し、Polisher は最小限の仕上げと監査ログ出力に専念する。

## モニタリング
- メトリクス: レンダリング時間、PDF 生成時間、警告件数、Polisher 実行率、Analyzer before/after の課題件数差分。
- ログ: ファイルパス、テンプレ版、LibreOffice exit code、修正内容（フォント調整など）、`monitoring_report.json` に基づくアラートサマリ。

## テスト戦略
- 単体: PH マッピング → スライド生成のロジックをモックで検証。
- 統合: サンプル spec で `output.pptx` と `rendering_log.json` を比較。
- 回帰: ゴールデンサンプルとの差分（ハッシュ）を CI で確認。
- PDF: `soffice --headless` の呼び出しテスト（CI ではスキップ可、ローカル推奨）。

## 未解決事項
- Polisher 適用後の差分ログ形式。
- LibreOffice のバージョン互換性（CI / ローカル混在環境）。
- 表の画像化フォールバックの詳細設計。
- 軽量整合チェックルールの拡張（表幅検知、レイアウトヒントとの突合など）。

## 関連スキーマ
- [docs/design/schema/stage-06-rendering.md](../schema/stage-06-rendering.md)
- サンプル: [docs/design/schema/samples/rendering_log.jsonc](../schema/samples/rendering_log.jsonc), [docs/design/schema/samples/audit_log.jsonc](../schema/samples/audit_log.jsonc)
