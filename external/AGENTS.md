# 基本原則
- 言語は日本語で統一する。
- コメントやメモで過去の変更に言及しない。

# external ディレクトリ向け作業指針

このディレクトリはテンプレート固有の外部フックと補助スクリプトを保管し、`uv run pptx ...` 実行時に CLI から呼び出されます。`docs/policies/context-engineering.md` の原則に従い、作業前に必要なドキュメントを確認してください。

## 1. フックの前提
- `external/` は git 管理外を前提としたローカル領域です。必要に応じて zip 等でバックアップ・配布してください。
- `uv run pptx template ... --layout-mode static --template-id <template_id>` を初めて実行すると、`external/<template_id>/hooks.json` のスケルトンが生成されます（既存ファイルがある場合は生成されません）。
- テンプレート ID と同名のサブディレクトリ（例: `external/sample/`）を用意し、`hooks.json` に stage 別の実行コマンドを登録します。
- CLI からは `PPTX_STAGE` / `PPTX_TEMPLATE_ID` / `PPTX_JOBSPEC_PATH` / `PPTX_TEMPLATE_PATH` / `PPTX_GENERATE_READY_PATH` / `PPTX_OUTPUT_DIR` などの環境変数が渡されます。
- 実行結果やキャッシュは `runtime/context.json` に保存されます。手動編集は避け、必要に応じてファイル削除でリセットします。

## 2. サブディレクトリ構成
- `assets/`: テンプレート固有の参照資料。初期状態では空の場合があります。
- `stageNN_*.py`: ステージごとのフックスクリプト。自動生成されないため、`external/sample/` をコピーして整備するか手動で作成してください。共有ロジックは `stage_shared.py` にまとめると保守しやすくなります。
- `mapping_config.json`: Excel など外部入力をマッピングする設定。JSON 形式で管理します。
- `.pptx/<template_id>/`: 一時成果物。`external/` には永続ファイルを残さないようにしてください。

## 3. 開発・テスト手順
1. `uv run pptx template` → `prepare` → `compose` → `gen` の順で実行し、外部フック経由でも成果物が生成されることを確認します。
2. フックスクリプト内では終了コードで成否を返し、標準出力・標準エラーは CLI ログへそのまま出力されます。ログの整形に注意してください。
3. スクリプトを単体検証したい場合は `uv run python external/<template_id>/stage02_prepare.py --help` のように直接実行します。
4. Excel や設定ファイルを更新した場合は README / AGENTS へ反映し、必要に応じて `.pptx/<template_id>/runtime/context.json` を削除して再検証します。

## 4. コーディングガイドライン
- Python 3.12 を想定しています。追加ライブラリが必要な場合は `uv sync` を利用するか、チームと合意のうえで導入してください。
- ファイルパス解決には `Path(__file__).resolve().parent` を用い、相対パス依存を避けます。
- `stage_shared.py` を更新した場合は影響範囲のフックをすべて再実行し、回帰を確認します。
- 新規テンプレートは `external/sample/` をコピーして着手し、不要ファイルを削除したうえでカスタマイズするのが安全です。

## 5. ドキュメント整備
- `external/README.md` にテンプレート追加手順や構成方針を記載しています。更新があれば README / AGENTS の両方を同期してください。
- 詳細な検討内容は `docs/notes/` に保存し、ToDo や PR から相互参照します。
- ToDo／ロードマップに紐づく作業は、Plan 承認後に記録し、完了時に該当項目を更新してください。
