# サポート・問い合わせ運用

## 連絡チャネル
- 緊急時: Slack `#pptx-generator`
- 通常の問い合わせ・改善要望: `docs/todo/` にトリアージ用 ToDo を作成し、進捗を管理する。

## 当番体制
- 運用時間外は当番表に従い、担当者が一次対応する。
- 当番は対応ログを ToDo または `docs/notes/` へ追加し、翌営業日までに共有する。

## 返信 SLA
- 初回応答: 営業日ベースで 1 日以内
- 進捗共有: 重大度に応じて 24〜48 時間ごと

## エスカレーション
1. 障害度を判断し、P0/P1 の場合は即座に Slack でコアメンバーへ通知する。
2. 必要に応じて Zoom / Meet を立ち上げ、影響範囲と暫定対応を確定する。
3. 復旧後、対応記録と恒久対策を ToDo に整理する。

## よくある問い合わせと対応テンプレート

- **レンダリング監査ログの確認方法**
  - `rendering_log.json` にスライド単位の検出結果と警告コードが記録されます。`missing_subtitle` / `empty_placeholder` / `missing_slide` などのコードを確認し、入力データやテンプレ側の欠落箇所を特定してください。
  - `audit_log.json.rendering` に警告件数や空プレースホルダー数が集計されています。Slack などで共有する際は `rendering_log.json` と合わせて添付し、該当スライド番号をコメントに記載します。
  - `audit_log.json.hashes` から `generate_ready` / `proposal.pptx` / `rendering_log` のハッシュを取得できるため、受領側で改ざん検知が可能です。

- **LibreOffice による PDF 変換が失敗する**
  - エラーコード `5`（CLI 終了コード）は PDF 変換ステップでの失敗を示す。
  - チェックリスト:
    - `LIBREOFFICE_PATH` を設定しているか、`soffice` が `PATH` に存在するか確認。
    - `uv run pptx gen <generate_ready.json> --export-pdf --pdf-timeout 180` などでタイムアウトを延長。（工程4と連携する場合は `pptx compose` / `pptx mapping` を併用）
    - `workdir/outputs/` に生成された `*.log`（LibreOffice 標準出力/エラー）を添付してもらう。
  - 暫定対応: `--pdf-mode both` で PPTX を受け取り、手動で PDF 変換する。
  - 恒久対応: LibreOffice のアップデート、権限設定、CI 上では `PPTXGEN_SKIP_PDF_CONVERT=1` を設定して PDF 変換をスキップし、別ジョブで PDF の有無を検証する。`audit_log.json.pdf_export` に `attempts` と `elapsed_ms` が出力されるため、リトライ状況を必ず確認する。
- **Polisher 実行が失敗する**
  - エラーコード `6` は Polisher ステップでの失敗を示す。`audit_log.json.polisher` の `status` と `stdout` / `stderr` を確認する。
  - チェックリスト:
    - 段落スタイル（揃え・行間・インデント）は Renderer がブランド設定から適用するため、Polisher はフォントサイズや色などフォールバック補正のみを担うことを前提に、ルール内容を確認する。
    - `config/rules.json` の `polisher.enabled` と `polisher.executable` が正しいか、`POLISHER_EXECUTABLE` 環境変数で上書きしていないか確認。
    - ルールファイル（例: `config/polisher-rules.json`）が存在し、JSON が壊れていないか検証（`jq` など）。
    - `uv run pptx gen ... --polisher-path <path> --polisher-timeout 180` などで再実行し、タイムアウト値を引き上げる。
    - `.NET 8` と Open XML SDK のバージョンがサポート対象か、`dotnet --info` の結果を共有してもらう。
    - CLI 標準出力の `Polisher: ...` および `Polisher Summary`、`audit_log.json.polisher.summary` を添付してもらう。処理時間は `elapsed_ms` を参照する。
  - 暫定対応: `--no-polisher` で CLI を実行し、Refiner の自動補正のみを適用した PPTX を納品する。必要に応じて手動で Polisher を実行。
  - 恒久対応: Polisher ルールセットや .NET プロジェクトのログ出力を改善し、`docs/runbooks` の個別 runbook に差分反映する。
