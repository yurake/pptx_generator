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
   - 最小構成: `samples/sample_spec_minimal.json`（テンプレート指定なしで 2 枚構成を確認）
   - フル構成: `samples/sample_spec.json`（テンプレートやアンカー利用例を含む 8 枚構成）
   - `.pptx` テンプレートを使う場合は CLI 実行時に `--template <パス>` を指定します。.potx には対応していないため、必要に応じて PowerPoint で `.pptx` に書き出してください。詳細は `docs/policies/config-and-templates.md` を参照してください。テンプレート例として `samples/templates/templates.pptx` を同梱しています。
2. CLI を実行して PPTX と analysis.json を生成します。
   ```bash
   uv run pptx-generator run samples/sample_spec_minimal.json
   # テンプレートを使う場合
   uv run pptx-generator run samples/sample_spec.json --template samples/templates/templates.pptx
   ```
   - `--workdir` は省略可能で、指定しない場合は `.pptxgen` が自動作成されます。
   - `--branding` でブランド設定 JSON を差し替えると、フォントやカラーが自動で反映されます。
   - `--export-pdf` を付与すると LibreOffice (soffice) を使って PDF を同時出力します。
     - `--pdf-mode=only` を指定すると PPTX を残さず PDF のみ保存します。
     - `--libreoffice-path` で soffice の場所を明示でき、`LIBREOFFICE_PATH` 環境変数も利用できます。
     - タイムアウトやリトライは `--pdf-timeout` / `--pdf-retries` で調整します。
    - 実行後は `outputs/audit_log.json` に生成時刻・メタ情報・PDF 変換結果が追記されます。
3. 生成物は `.pptxgen/outputs/` 配下に保存されます。

## テスト・検証
- レンダラー・CLI を含むテストスイートを pytest で実行できます。
  ```bash
  uv run --extra dev pytest
  ```
  - CLI 統合テストでは PPTX 出力と analysis.json を検証し、レンダラー単体テストで表・画像・グラフの描画ロジックを確認します。

## 設定
- `config/rules.json`: タイトル・箇条書きの文字数、段落レベル、禁止ワードを定義します。
- `config/branding.json`: デフォルトのフォントやブランドカラーを定義します。
