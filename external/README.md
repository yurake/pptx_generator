# external ディレクトリ概要

`external/` はテンプレート固有のフックや補助スクリプトを配置するローカル運用領域です。`uv run pptx ...` 実行時に CLI がテンプレート ID を基に該当ディレクトリを探索し、`hooks.json` で定義されたスクリプトを呼び出します。

## 構成

```
external/
├── README.md               # 本ファイル
├── AGENTS.md               # 作業指針
├── demo_tpl/               # 雛形サンプル
└── sample/                 # テンプレート ID ごとのサブディレクトリ例
    ├── assets/             # 参照資料（テンプレ PPTX / 入力サンプル等）
    ├── hooks.json          # stage & slide 別フック定義
    ├── mapping_config.json # Excel → PPTX マッピング設定
    ├── runtime/            # 実行時キャッシュ（template_path など）
    ├── stage02_prepare.py  # Stage2 フック
    ├── stage04_gen.py      # Stage4 フック
    └── stage_shared.py     # 共通ユーティリティ
```

- サブディレクトリ名はテンプレート ID と一致させてください。`jobspec.meta.template_id` から解決されます。
- `hooks.json` は `stage.<name>`（`template`/`prepare`/`compose`/`mapping`/`gen`）ごとに `{ "command": ..., "args": [...] }` を指定します。`continue_default: true` でフック実行後に標準処理を継続できます。
- `slides` セクションはスライド単位の追加フック用の予約領域です。
- `runtime/` 配下のファイルは CLI が自動更新します。手動編集は避けてください。
- `external/` 全体は git 管理外のローカル領域を想定しています。共有が必要な場合は zip 等で配布し、README / AGENTS のみリポジトリにコミットします。

## 新しいテンプレートを追加するには

1. `uv run pptx template templates/<file>.pptx --layout-mode static --template-id <template_id> ...` を一度実行し、`.pptx/<template_id>/` の成果物と同時に `external/<template_id>/hooks.json` のスケルトンを生成します（既存ファイルがある場合は生成されません）。
2. Stage フックスクリプトは自動生成されないため、`external/sample/` など既存構成をコピーするか、新規に `stageNN_*.py` / `stage_shared.py` を作成して `hooks.json` から参照してください。
3. 必要に応じて `assets/` 配下へテンプレ PPTX や入力サンプルを配置し、スクリプトが参照するパスと一致させます（初期状態では空ディレクトリの場合があります）。
4. `uv run pptx prepare ...` → `compose` → `gen` を実行し、`.pptx/<template_id>/` に期待する成果物が生成されるか確認します。再検証時は `.pptx/<template_id>/` や `external/<template_id>/runtime/context.json` を削除してから実行するとキャッシュがクリアされます。

## 注意事項

- テンプレート固有の秘密情報（API キー等）を配置しないでください。必要な場合は環境変数で渡します。
- `hooks.json` の変更は CLI 実行ログに影響します。標準出力・エラーは CLI ログへそのまま出力されるため、メッセージの可読性を意識してください。
- `.pptx/` 配下は常に再生成される一時領域です。恒久的なスクリプトや設定ファイルは `external/` に保管し、コミット対象としては README / AGENTS のみ管理します。
