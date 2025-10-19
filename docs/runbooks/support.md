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

- **LibreOffice による PDF 変換が失敗する**
  - エラーコード `5`（CLI 終了コード）は PDF 変換ステップでの失敗を示す。
  - チェックリスト:
    - `LIBREOFFICE_PATH` を設定しているか、`soffice` が `PATH` に存在するか確認。
    - `uv run pptx render <rendering_ready.json> --export-pdf --pdf-timeout 180` などでタイムアウトを延長。（工程5と連携する場合は `pptx gen` / `pptx mapping` を併用）
    - `workdir/outputs/` に生成された `*.log`（LibreOffice 標準出力/エラー）を添付してもらう。
  - 暫定対応: `--pdf-mode both` で PPTX を受け取り、手動で PDF 変換する。
  - 恒久対応: LibreOffice のアップデート、権限設定、CI 上では `PPTXGEN_SKIP_PDF_CONVERT=1` を設定して PDF 変換をスキップし、別ジョブで PDF の有無を検証する。
