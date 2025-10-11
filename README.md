# pptx_generator

JSON 仕様から PowerPoint 提案書を自動生成するツールです。タイトルや箇条書きに加えて、ブランド設定に基づく表・画像・グラフの描画と簡易解析をサポートしています。

## セットアップ
1. Python 3.12 系の仮想環境を用意します。
2. 依存関係をインストールします。
   ```bash
   uv sync
   ```

## 使い方
1. サンプル JSON を参考に入力仕様を整えます。
   - 最小構成: `samples/json/sample_spec_minimal.json`（テンプレート指定なしで 2 枚構成を確認）
   - フル構成: `samples/json/sample_spec.json`（テンプレートやアンカー利用例を含む 8 枚構成）
   - `.pptx` テンプレートを使う場合は CLI 実行時に `--template <パス>` を指定します。.potx には対応していないため、必要に応じて PowerPoint で `.pptx` に書き出してください。詳細は `docs/policies/config-and-templates.md` を参照してください。テンプレート例として `samples/templates/templates.pptx` を同梱しています。
2. CLI を実行して PPTX と analysis.json を生成します。
   ```bash
   uv run pptx-generator run samples/json/sample_spec_minimal.json
   # テンプレートを使う場合
   uv run pptx-generator run samples/json/sample_spec.json --template samples/templates/templates.pptx
   ```
   - 実行後は `outputs/audit_log.json` に生成時刻・メタ情報・PDF 変換結果が追記されます。
3. テンプレートの構造解析を行う場合は `extract-template` コマンドを使用します。
   ```bash
   # 基本的な使用方法
   uv run pptx-generator extract-template --template samples/templates/templates.pptx
   
   # 特定のレイアウトのみを抽出
   uv run pptx-generator extract-template --template samples/templates/templates.pptx --layout "タイトルスライド"
   
   # YAML形式で出力
   uv run pptx-generator extract-template --template samples/templates/templates.pptx --format yaml
   ```
   - 既存の `.pptx` テンプレートから JSON 仕様の雛形を生成し、テンプレートの構造を解析してアンカー情報や座標データを含む雛形 JSON を作成します。

| Option | Function | Default |
| --- | --- | --- |
| `--template <path>` | 利用する `.pptx` テンプレートを指定する | python-pptx 同梱テンプレート |
| `--workdir <path>` | ワークスペース（出力先）を変更する | `.pptxgen` |
| `--branding <path>` | ブランド設定 JSON を差し替える | `config/branding.json` |
| `--export-pdf` | LibreOffice 経由で PDF を同時生成する | 無効 |
| `--pdf-mode=only` | PPTX を生成せず PDF のみ出力する | `full`（PPTX と PDF の両方を生成） |
| `--libreoffice-path <path>` | soffice の実行パスを明示する | `PATH` 検索結果 |
| `--pdf-timeout <sec>` | LibreOffice 実行のタイムアウト秒数を設定する | 60 |
| `--pdf-retries <count>` | PDF 変換のリトライ回数を指定する | 0 |

### extract-template 専用オプション

| Option | Function | Default |
| --- | --- | --- |
| `--template <path>` | 解析する `.pptx` テンプレートを指定（必須） | - |
| `--output <path>` | 出力ファイル名を指定 | `template_spec.json` |
| `--layout <keyword>` | レイアウト名に部分一致するキーワードで抽出対象を絞り込む | 全レイアウト |
| `--anchor <keyword>` | アンカー名に部分一致するキーワードで抽出対象を絞り込む | 全アンカー |
| `--format <json\|yaml>` | 出力形式を指定 | `json` |
| `--verbose` | 詳細ログを表示 | 無効 |

4. 生成物は `--workdir` 未指定の場合 `.pptxgen/outputs/` に保存されます。

## テスト・検証
- レンダラー・CLI を含むテストスイートを pytest で実行できます。
  ```bash
  uv run --extra dev pytest
  ```
  - CLI 統合テストでは PPTX 出力と analysis.json を検証し、レンダラー単体テストで表・画像・グラフの描画ロジックを確認します。

## 設定
- `config/rules.json`: タイトル・箇条書きの文字数、段落レベル、禁止ワードを定義します。
- `config/branding.json`: デフォルトのフォントやブランドカラーを定義します。
