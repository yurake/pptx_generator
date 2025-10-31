# リリース手順

## 事前準備
- テンプレートおよび設定ファイルのバージョンを確認し、必要に応じてインクリメントする。
- `config/branding.json` が `version: "layout-style-v1"` であること、`docs/design/layout-style-governance.md` に記載のスタイル定義とズレがないことを確認する。
- `docs/todo/` の対応タスクを最新化し、残作業が無いことを確認する。
- `uv run --extra dev pytest` を実行し、スタイル設定を含む全テストがグリーンであることを確認する。
- CI がグリーンであることをダッシュボードで確認する。

## 手順
1. `CHANGELOG.md` を更新し、主要変更点と既知の注意点を記載する。
2. ステージング環境で代表的な案件データ（最低 3 件）を用いて JSON→PPTX→PDF の生成テストを実施する。
3. テンプレート更新が含まれる場合は `uv run pptx layout-validate --template samples/templates/templates.pptx --output .pptx/validation/release` を実行し、`diagnostics.json` にエラーが無いことと `layouts.jsonl` の差分を確認する。必要に応じて `samples/json/sample_template_layouts.jsonl` / `sample_jobspec.json` を同期する。
4. 監査ログ、通知動作、PDF 変換など重要機能を確認し、承認者のレビューを取得する。
5. テンプレ受け渡しメタの `analyzer_metrics` と差分レポートの `analyzer` ブロックを確認し、重大度別の指摘推移を記録する。
   - `summary` / `summary_delta` セクションでレイアウト数・アンカー数・警告件数・Analyzer issue/fix 件数を確認する。
   - `environment` セクションで Python / LibreOffice / .NET SDK のバージョンを控え、CI と一致しているか照合する。
6. タグ `vX.Y.Z` を付与し、GitHub Release を作成する。
7. デプロイを実施し、完了後にステータスを共有する。

## 環境バージョン固定とゴールデンサンプル運用
- LibreOffice / dotnet SDK は CLI 実行環境と揃うようにインストール版を固定し、`template_release.json` の `environment` に記録されるバージョンと突合する。
- Polisher (.NET) のアップデートを行う場合は、`dotnet --version` で SDK を確認し `docs/notes/` に差分メモを残す。
- `tpl-release --baseline-release` 実行時はベースラインの `golden_runs` を自動再実行する。不要なゴールデンサンプルがあればベースラインの `golden_runs.json` から削除し、差分の理由を ToDo に記載する。
- ゴールデンサンプル成果物は `templates/releases/<brand>/<version>/golden_runs/` に 3 リリース分保持し、それ以前はハッシュとログのみ残して削除する（廃棄時は `docs/notes/` に記録）。

## ロールバック
- 重大障害発生時は直前のタグへロールバックし、影響範囲と復旧時間を `docs/notes/` に記録する。
- ロールバック後は原因分析と恒久対応を ToDo として整理する。
- レイアウトスタイルに起因する不具合の場合は `config/branding.json` を直前タグから復元し、`docs/design/layout-style-governance.md` の差分を確認して関係者へ共有する。
