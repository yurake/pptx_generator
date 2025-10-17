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
| Analyzer Snapshot Linker | Analyzer スナップショットと抽出結果の突合 | Python |

## 処理フロー
1. PPTX 読み込み → マスター階層を列挙。  
2. 各レイアウトのプレースホルダを収集し、`type`, `name`, `bbox`, `style_hint` を付与。  
3. 面積・アスペクト比から `text_hint`, `media_hint` を計算。  
4. 用途タグ推定（レイアウト名、PH パターン、ヒューリスティック）。  
5. JSON Lines 形式で `layouts.jsonl` に書き出し。  
6. スキーマ検証 → 警告項目を `diagnostics.json` にまとめる。  
7. `--baseline` 指定時は過去バージョンと比較し、差異を `diff_report.json` として出力。  
8. `--analyzer-snapshot` が指定された場合は Analyzer が出力した `analysis_snapshot.json` を読み込み、アンカー命名やレイアウトの整合を突合する。欠落・未定義アンカーを `diagnostics.json` と `diff_report.json` の `issues` に追加する。

## CLI 実行例
```bash
uv run pptx tpl-extract \
  --template templates/libraries/acme/v1/template.pptx \
  --output .pptx/extract/acme_v1
```

### 検証スイート
```bash
uv run pptx layout-validate \
  --template templates/libraries/acme/v1/template.pptx \
  --output .pptx/validation/acme \
  --baseline releases/acme/v0/layouts.jsonl
```

- `layouts.jsonl` / `diagnostics.json` / `diff_report.json` を同時生成し、`jsonschema` でスキーマ検証を実施。
- `--template-id` でテンプレート識別子を上書き可能。未指定時はファイル名から導出する。
- `warnings`（重複 PH、未知種別など）と `errors`（抽出失敗、必須項目欠落）を集計し、差分レポートではプレースホルダーの追加・削除・位置変更を検知する。
- Analyzer と連携する際は `pptx gen --emit-structure-snapshot` で生成した `analysis_snapshot.json` を `--analyzer-snapshot` に指定し、命名漏れ・未知のアンカーを検出する。

## エラーハンドリング
- PH 抽出失敗 → `diagnostics.json` に `error` レベルで記録し exit code 1。
- 未対応 PH 種別 → `warning` で `placeholders[i].type=unknown` とする。
- 差分比較失敗（ベース無し）は警告のみ。

## メトリクス / ログ
- 解析時間、レイアウト数、PH 総数、警告件数を出力。
- 差分レポートでは追加/削除/変更の件数とリストを記録。

## 主要成果物
### diagnostics.json
- プレースホルダー抽出時の `warnings` / `errors` を記録する中核成果物。
- Analyzer スナップショットを突合した結果は以下のコードで追記される。
  - `analyzer_anchor_missing`: 抽出結果に存在するがスナップショットから欠落しているアンカー。
  - `analyzer_anchor_unexpected`: スナップショット側にのみ存在するアンカー。
  - `analyzer_placeholder_unnamed`: スナップショットで名称が欠落しているプレースホルダー。
- `stats` にはレイアウト数・プレースホルダー総数・処理時間を記録し、CI の回帰チェックに活用する。

### diff_report.json
- `--baseline` が指定された場合は従来通りの差分計算を実施する。
- Analyzer 連携のみであっても、検出したアンカー差分は `issues[]` に追記したうえで `diff_report.json` を生成する。`baseline_template_id` には `__analyzer_snapshot__` を設定する。

### analysis_snapshot.json
- `pptx gen --emit-structure-snapshot` で生成される Analyzer の補助成果物。
- スライド単位で `placeholders`（図形の `shape_id` / `name` / `placeholder_type` / 位置情報）と `named_shapes`（アンカー候補）、`spec_anchors`（ジョブ仕様で参照されたアンカー）を記録する。
- `layout-validate --analyzer-snapshot` に渡すことで抽出結果とジョブ実体の命名整合性を自動チェックできる。

## テスト
- 単体: 代表テンプレの解析結果を golden JSON と比較。
- 回帰: CI で `tests/data/templates/*.pptx` を解析し、差分ゼロを確認。
- `tests/test_layout_validation_suite.py` で CLI・差分検証・スキーマ検証の回帰を担保。

## 未解決事項
- ヒント係数の計算式とチューニング方法。
- 用途タグ推定に LLM / ML を使うかヒューリスティックで維持するか。
- `analysis_snapshot.json` のスキーマ拡張とバージョン管理ポリシー。

## 関連スキーマ
- [docs/design/schema/stage-02-template-structure-extraction.md](../schema/stage-02-template-structure-extraction.md)
- サンプル: `docs/design/schema/samples/layouts.jsonl`（準備予定）、`docs/design/schema/samples/diagnostics.jsonc`（準備予定）
