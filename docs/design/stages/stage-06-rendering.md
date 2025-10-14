# 工程6 PPTX レンダリング 設計

## 目的
- `rendering_ready.json` とテンプレートを用いて最終 `output.pptx` を生成し、軽量整合チェックと監査ログを出力する。
- LibreOffice PDF 変換や Open XML Polisher との統合を考慮した拡張性を持たせる。

## コンポーネント
| コンポーネント | 役割 | 技術 |
| --- | --- | --- |
| Rendering Orchestrator | スライド生成・PH 挿入・ノート/フッター設定 | Python (`python-pptx`) |
| Consistency Checker | 空要素、レイアウト不一致、表サイズ超過の検証 | Python |
| Audit Logger | `rendering_log.json`, `audit_log.json` の生成 | Python |
| PDF Converter | LibreOffice headless で PDF 出力 | CLI (`soffice`) |
| Polisher Bridge | Open XML SDK プロジェクト呼び出し | .NET 8 CLI |

## フロー
1. Rendering Orchestrator がテンプレートを開き、章情報を元にスライドを生成。  
2. 各 PH にテキスト・表・画像を挿入し、フォーマット調整。  
3. Consistency Checker が空 PH、表の溢れ、layout mismatch をチェック。  
4. 問題があれば自動修正 or 警告として `rendering_log.json` に記録。  
5. 監査メタ (`audit_log.json`) と生成ログを保存。  
6. `--export-pdf` 指定時は LibreOffice を呼び出し PDF を生成。  
7. Polisher Bridge を起動して Open XML Polisher を実行（任意）。

## ログ / 成果物
- `rendering_log.json`: スライド毎の `layout_id`, 挿入要素数, 警告一覧, 所要時間。
- `audit_log.json`: テンプレ版、入力ハッシュ、生成ハッシュ、処理パイプライン履歴。
- `stdout`: 主要な処理ステップと警告を INFO レベルで出力。

## エラーハンドリング
- 要素挿入失敗 → スライド番号と PH を特定してログ化、exit code 1。
- LibreOffice 失敗 → 再試行制御（最大 3 回）、それでも失敗なら `pdf_status=failed`。
- Polisher 失敗 → PPTX は保持しつつ警告を出力。

## 設定項目
- `rendering.max_table_width_pt`, `rendering.bullet_line_spacing`, `rendering.default_note_template`
- `pdf.retry_limit`, `pdf.timeout_sec`
- `polisher.enabled`, `polisher.binary_path`, `polisher.rules_path`

## モニタリング
- メトリクス: レンダリング時間、PDF 生成時間、警告件数、Polisher 実行率。
- ログ: ファイルパス、テンプレ版、LibreOffice exit code、修正内容（フォント調整など）。

## テスト戦略
- 単体: PH マッピング → スライド生成のロジックをモックで検証。
- 統合: サンプル spec で `output.pptx` と `rendering_log.json` を比較。
- 回帰: ゴールデンサンプルとの差分（ハッシュ）を CI で確認。
- PDF: `soffice --headless` の呼び出しテスト（CI ではスキップ可、ローカル推奨）。

## 未解決事項
- Polisher 適用後の差分ログ形式。
- LibreOffice のバージョン互換性（CI / ローカル混在環境）。
- 表の画像化フォールバックの詳細設計。
