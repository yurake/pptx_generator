# pptx_generator

JSON 仕様から PowerPoint 提案書を自動生成する開発中のツールです。現時点では基本的なスライド構成と簡易解析のみをサポートしています。

## セットアップ
1. Python 3.12 系の仮想環境を用意します。
2. 依存関係をインストールします。
   ```bash
   uv sync
   ```

## 使い方
1. サンプル JSON `samples/sample_spec.json` を基に編集し、案件情報を準備します。
2. CLI を実行して PPTX と analysis.json を生成します。
   ```bash
   uv run pptx-generator run samples/sample_spec.json
   ```
   - `--workdir` は省略可能で、指定しない場合は `.pptxgen` が自動作成されます。
3. 生成物は `.pptxgen/outputs/` 配下に保存されます。

## 検証
- CLI の実行と生成物の内容をまとめて確認する場合は、以下のスクリプトを利用できます。
  ```bash
  uv run python scripts/verify_cli_outputs.py
  ```
  - 標準では `samples/sample_spec.json` を入力に使用し、`analysis.json` と `proposal.pptx` の内容を検証します。

## 設定
- `config/rules.json`: タイトル・箇条書きの文字数、段落レベル、禁止ワードを定義します。
- `config/branding.json`: デフォルトのフォントやブランドカラーを定義します。

## 今後の予定
- PPTX レイアウトの詳細制御、画像や表の配置
- 自動診断の高度化（余白・禁則チェックなど）
- CLI および API の統合テスト整備
