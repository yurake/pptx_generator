# リリース手順

## 事前準備
- テンプレートおよび設定ファイルのバージョンを確認し、必要に応じてインクリメントする。
- `pptx template` の出力物（`.pptx/template/branding.json` など）が `version: "layout-style-v1"` であり、`docs/design/stages/stage-01-style-governance.md` に記載のスタイル定義と整合していることを確認する。
- Template AI 用の環境変数（`PPTX_TEMPLATE_LLM_PROVIDER`、`PPTX_TEMPLATE_LLM_MODEL` など）が本番想定と一致しているか確認し、`src/pptx_generator/config/usage_tags.json` にある canonical タグと説明が最新であることをレビューする。`mock` 以外を利用する場合は API キーやエンドポイントを secrets に登録済みか再確認する。
- `docs/todo/` の対応タスクを最新化し、残作業が無いことを確認する。
- `uv run --extra dev pytest` を実行し、スタイル設定を含む全テストがグリーンであることを確認する。
- CI がグリーンであることをダッシュボードで確認する。
- 静的テンプレで外部フック（`external/<template_id>/hooks.json`）を利用している場合は、同ディレクトリの `pyproject.toml` / `uv.lock` が最新か確認し、必要なら `uv sync --project external/<template_id>` を実行して依存を整えておく（CLI はフック実行前に同コマンドを自動実行するが、リリース前に同期漏れがないかチェックする）。

## 手順
1. `CHANGELOG.md` を更新し、主要変更点と既知の注意点を記載する。
2. ステージング環境で代表的な案件データ（最低 3 件）を用いて JSON→PPTX→PDF の生成テストを実施する。
   - 静的テンプレート＋外部フックを利用する案件は Excel 入力を含む静的パイプラインを実行し、`.pptx/<slug>/gen/` に出力された PPTX の表セルと `external/<template_id>/runtime/context.json` の `extract_summary.table` を `scripts/inspect_static_pptx.py` で突合する。

     ```bash
     uv run python scripts/inspect_static_pptx.py \
       --template templates/経費投資.pptx \
       --pptx .pptx/jri/gen/jri_static_output.pptx \
       --slide-index 0
     ```

     出力結果から表セルやプレースホルダーの文言を確認し、`context.json` の `extract_summary.table` と一致しているかをレビューする。
3. テンプレート更新が含まれる場合は `uv run pptx layout-validate --template samples/templates/templates.pptx --output .pptx/validation/release` を実行し、`diagnostics.json` にエラーが無いことと `layouts.jsonl` の差分を確認する。必要に応じて `samples/json/sample_template_layouts.jsonl` / `samples/json/sample_jobspec.json` / `samples/extract/jobspec.json` を同期する。
   - `diagnostics.json.template_ai` を確認し、生成 AI が `usage_tags` を返しているか、未知タグやエラーが無いかをレビューする。`mock` フォールバックの場合は静的ルールによりタグが採用されていることを確認し、本番運用では環境変数で LLM を有効化する。
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
- レイアウトスタイルに起因する不具合の場合はテンプレートを直前タグから復元し、`pptx template` で再抽出した TemplateStyle（`branding.json` スナップショット含む）と `docs/design/stages/stage-01-style-governance.md` の差分を確認して関係者へ共有する。
