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
- `analysis_pre_polisher.json`: Renderer 直後の Analyzer 結果。Polisher/LibreOffice 実行による改善度を算出するベースライン。
- `rendering_log.json`: スライドごとの整合チェック結果（検出要素フラグ、警告コード、空プレースホルダー件数）とメタ情報（テンプレ版、生成時間、警告件数総計）。
- `monitoring_report.json`: `rendering_log.json` と Analyzer before/after を突合した監視レポート。スライド単位のアラートと改善メトリクスを保持する。
- 監査ログ (`audit_log.json`): 生成物ハッシュ、`rendering_log.json` / `monitoring_report.json` への参照、整合チェックサマリ、`pdf_export` / `polisher` 実行メタ（有効可否、ステータス、実行時間、リトライ回数）、`monitoring_summary` を含む。
- 必要に応じて PDF。
- 実行ログ: CLI 標準出力に `Polisher: <status>` とサマリ JSON を出力し、整合チェックの警告件数・`monitoring_report.json` 出力先を INFO レベルで通知する。

## ワークフロー
1. テンプレ PPTX を読み込み、`rendering_ready.json` から再構築した章構造とスライドを初期化する。
2. 章順にスライドを追加し、各 PH にテキスト・表・注記・ロゴを挿入する。
3. ノート欄やフッター等のテンプレ設定を反映する。
4. 軽量整合チェック（空プレースホルダー、スライド数不一致、主要要素の欠落）を実施し、結果を `rendering_log.json` にまとめる。
5. チェック結果の警告件数と代表メッセージを CLI ログへ出力する。
6. Renderer 出力直後に Analyzer を実行し、`analysis_pre_polisher.json` を生成する（スナップショット出力は任意）。
7. `polisher.enabled` または `--polisher` 指定時に Open XML Polisher を呼び出す。
8. Polisher 実行後の PPTX を対象に整合チェックを再評価し（必要に応じて差分を追記）、`polisher` メタを監査ログへ反映する。
9. `--export-pdf` 指定時は LibreOffice で PDF を生成し、リトライ回数と所要時間を監査ログへ記録する。`pdf-mode=only` の場合でも Analyzer 後までは PPTX を保持し、監視レポート生成後に削除する。
10. Analyzer が Polisher / LibreOffice 実行後の PPTX を再解析し、`analysis.json` とスナップショットを作成する。
11. Monitoring Integration ステップが `rendering_log.json` と Analyzer before/after を突合し、`monitoring_report.json` と `monitoring_summary` を生成する。

## 品質ゲート
- `output.pptx` が正常に開けること。
- 重大な警告（テンプレ不一致、空要素）がない、または解決済みである。
- 監査メタにテンプレ版、`rendering_ready` ハッシュ、生成時間、`monitoring_summary.alert_level` が記録されている。
- PDF 変換が有効な場合、`soffice` でエラーなく生成される。`pdf-mode=only` の場合は `pptx_path` が監視ステップ後に確実に削除される。
- Polisher が有効な場合、CLI は exit code 0 で終了し、`audit_log.json.polisher.status=success` を記録する。無効な場合は `status=disabled` を出力する。
- Monitoring Summary の `alert_level` が `critical` の場合は CI / 運用通知でフォローアップする仕組みが整備されている（通知先連携は別タスクで実装）。

## 監査・運用
- 生成ログに差分検知（layout mismatch、Auto-fix 適用）を記録する。
- 監査ログと承認ログを `slide_uid` で突合可能にする。
- フォールバック適用時（表の画像化等）は事後対応ガイドを同梱する。
- Polisher 実行結果（実行可否、所要時間、ルールパス、サマリ JSON）と PDF 変換結果（リトライ回数、所要時間、使用コンバータ、モード）を `audit_log.json` に記録する。
- `rendering_ready.json`・`proposal.pptx`・`analysis_pre_polisher.json`・`analysis.json`・`monitoring_report.json`・PDF（生成時）のハッシュを `audit_log.json.hashes` に格納し、監査ログから検証できる状態を保つ。
- `monitoring_summary` を監査ログへ記録し、CI から alert level / headline を即時参照できるようにする。

## 未実装項目（機能単位）
- 軽量整合チェックルールの実装と警告ハンドリング。
- 生成ログと承認ログを結合する監査メタ拡張。
- Polisher 適用後の差分ログ設計とルールセット管理。
