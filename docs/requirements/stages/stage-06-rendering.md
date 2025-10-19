# 工程6 PPTX 生成 要件詳細

## 概要
- テンプレ PPTX と `rendering_ready.json` を使用し、最終 `output.pptx` と付随ログを生成する。`rendering_ready` に含まれる `job_meta` / `job_auth` から `JobSpec` を再構成する。
- 軽量整合チェックと監査メタの付与を自動化し、配布前の品質を確保する。
- CLI は `uv run pptx render <rendering_ready.json>` を基本とし、`uv run pptx gen` は工程5/6をまとめて実行する。

## 入力
- 工程5の `rendering_ready.json`（`job_meta` / `job_auth` を内包）。
- 工程1のテンプレ PPTX、および任意のロゴアセット。
- ブランド設定 JSON、レンダリング構成（フォント置換、行間調整などのポリシー）。
- Polisher ルール (`config/polisher-rules.json` など任意ファイル)。有効化時に必須。

## 出力
- `output.pptx`（最終成果物）。
- `rendering_log.json`: テンプレ版、使用 `layout_id`、挿入要素数、警告一覧、処理時間。
- 監査ログ (`audit_log.json`): テンプレ版、ハッシュ、`pdf_export` / `polisher` メタ。
- 必要に応じて PDF。
- 実行ログ: CLI 標準出力に `Polisher: <status>` とサマリ JSON を出力し、運用フローから確認可能にする。

## ワークフロー
1. テンプレ PPTX を読み込み、`rendering_ready.json` から再構築した章構造とスライドを初期化する。
2. 章順にスライドを追加し、各 PH にテキスト・表・注記・ロゴを挿入する。
3. ノート欄やフッター等のテンプレ設定を反映する。
4. 軽量整合チェック（空要素、表のはみ出し、layout mismatch、過剰改行）を実施する。
5. 必要に応じて表の列幅調整や画像化を行い、警告を記録する。
6. ファイルを保存し、生成ログと監査メタを出力する。
7. `polisher.enabled` または `--polisher` 指定時に Open XML Polisher を呼び出す。
8. Analyzer が生成済み PPTX を再解析し、`analysis.json` とスナップショットを作成する。
9. `--export-pdf` 指定時は LibreOffice で PDF を生成する。

## 品質ゲート
- `output.pptx` が正常に開けること。
- 重大な警告（テンプレ不一致、空要素）がない、または解決済みである。
- 監査メタにテンプレ版、`rendering_ready` ハッシュ、生成時間が記録されている。
- PDF 変換が有効な場合、`soffice` でエラーなく生成される。
- Polisher が有効な場合、CLI は exit code 0 で終了し、`audit_log.json.polisher.status=success` を記録する。無効な場合は `status=disabled` を出力する。

## 監査・運用
- 生成ログに差分検知（layout mismatch、Auto-fix 適用）を記録する。
- 監査ログと承認ログを `slide_uid` で突合可能にする。
- フォールバック適用時（表の画像化等）は事後対応ガイドを同梱する。
- Polisher 実行結果（コマンド・所要時間・ルールセット）は `audit_log.json.polisher` に記録し、runbook の手順で確認する。

## 未実装項目（機能単位）
- 軽量整合チェックルールの実装と警告ハンドリング。
- 生成ログと承認ログを結合する監査メタ拡張。
- Polisher 適用後の差分ログ設計とルールセット管理。
