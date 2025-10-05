# pptx_generator

JSON 仕様から PowerPoint 提案書を自動生成するツールです。タイトルや箇条書きに加えて、ブランド設定に基づく表・画像・グラフの描画と簡易解析をサポートしています。

## セットアップ
1. Python 3.12 系の仮想環境を用意します。
2. 依存関係をインストールします。
   ```bash
   uv sync
   ```

## 使い方
1. サンプル JSON `samples/sample_spec.json` を基に編集し、案件情報とスライド要素（表・画像・グラフ）を準備します。
2. CLI を実行して PPTX と analysis.json を生成します。
   ```bash
   uv run pptx-generator run samples/sample_spec.json
   ```
   - `--workdir` は省略可能で、指定しない場合は `.pptxgen` が自動作成されます。
    - `--branding` でブランド設定 JSON を差し替えると、フォントやカラーが自動で反映されます。
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
