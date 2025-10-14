# 工程2 テンプレ構造抽出 設計

## 目的とスコープ
- `.pptx` からレイアウト情報を抽出し、工程 3〜5 の基礎データ (`layouts.jsonl`, `diagnostics.json`) を生成。
- テンプレ差分検証やレイアウト品質の自動診断を担う。

## コンポーネント
| コンポーネント | 概要 | 主実装 |
| --- | --- | --- |
| `TemplateExtractorStep` | スライドマスター走査、PH 抽出、ヒント算出 | Python (`python-pptx`) |
| Schema Validator | `layouts.jsonl` スキーマ検証、欠落項目の報告 | Python (`jsonschema`) |
| Diff Reporter | 過去バージョンとの差分レポート生成 | Python (`deepdiff`) |
| Diagnostics Aggregator | 警告・エラーの集計と `diagnostics.json` 出力 | Python |

## 処理フロー
1. PPTX 読み込み → マスター階層を列挙。  
2. 各レイアウトのプレースホルダを収集し、`type`, `name`, `bbox`, `style_hint` を付与。  
3. 面積・アスペクト比から `text_hint`, `media_hint` を計算。  
4. 用途タグ推定（レイアウト名、PH パターン、ヒューリスティック）。  
5. JSON Lines 形式で `layouts.jsonl` に書き出し。  
6. スキーマ検証 → 警告項目を `diagnostics.json` にまとめる。  
7. `--baseline` 指定時は過去バージョンと比較し、差異を `diff_report.json` として出力。

## CLI 実行例
```bash
uv run extract-template templates/libraries/acme/v1/template.pptx \
  --output layouts.jsonl \
  --diagnostics diagnostics.json \
  --baseline releases/acme/v0/layouts.jsonl
```

## エラーハンドリング
- PH 抽出失敗 → `diagnostics.json` に `error` レベルで記録し exit code 1。
- 未対応 PH 種別 → `warning` で `placeholders[i].type=unknown` とする。
- 差分比較失敗（ベース無し）は警告のみ。

## メトリクス / ログ
- 解析時間、レイアウト数、PH 総数、警告件数を出力。
- 差分レポートでは追加/削除/変更の件数とリストを記録。

## テスト
- 単体: 代表テンプレの解析結果を golden JSON と比較。
- 回帰: CI で `tests/data/templates/*.pptx` を解析し、差分ゼロを確認。

## 未解決事項
- ヒント係数の計算式とチューニング方法。
- 用途タグ推定に LLM / ML を使うかヒューリスティックで維持するか。
- `diagnostics.json` を Analyzer/Renderer へ連携するインターフェース。

## 関連スキーマ
- [docs/design/schema/overview.md](../schema/overview.md)
