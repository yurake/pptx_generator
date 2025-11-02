# 工程2 テンプレ構造抽出 要件詳細

## 概要
- テンプレ PPTX からレイアウト構造を機械抽出し、工程 3〜5 が利用できる JSON を生成する。
- 抽出処理は自動バッチで実行し、結果の妥当性検証と差分診断を行う。

## 入力
- 工程1で承認されたテンプレ PPTX。
- プレースホルダ種別マッピング表、面積→ヒント係数計算ルール。
- 既存レイアウトカタログ（過去バージョンとの差分照合に利用）。
- Analyzer が生成した構造スナップショット (`analysis_snapshot.json`, 任意)。テンプレ抽出結果との突合に利用する。

## 出力
- `layouts.jsonl`: テンプレ ID、レイアウト ID、プレースホルダ一覧、テキスト/メディアヒント、用途タグ。
- `diagnostics.json`: 抽出警告・エラー、欠落レイアウト、フォールバック処理の記録。
- `jobspec.json`: レイアウト名ごとのスライド雛形とプレースホルダー情報。工程3～5 がテンプレ依存の座標やアンカー名を参照するための catalog。
- 差分レポート: 過去バージョンとの差異、命名変更、欠落 PH など。Analyzer 突合のみの場合でも、検出結果を `issues` に含めたレポートを出力する。

## ワークフロー
1. 解析ジョブがテンプレ PPTX を取得し、スライドマスター配下のレイアウトを列挙する。
2. 各レイアウトのプレースホルダを抽出し、種別・面積・座標を付与する。
3. 抽出結果からテンプレ依存情報のみを集約した `jobspec.json` を生成し、スライド ID・アンカー名・プレースホルダ種別・座標・サンプルテキストを catalog 化する。
4. レイアウトカテゴリ・用途タグを決定し、ヒント係数を算出する。
5. JSON スキーマ検証を行い、欠落 PH や抽出不能項目を診断する。
6. 過去バージョンとの比較を行い、差分レポートを生成する。
7. `analysis_snapshot.json` が提供されている場合はプレースホルダー命名を突合し、欠落・未知アンカーを `diagnostics.json` と差分レポートへ追加する。
8. 結果をアーカイブし、工程 3 以降に引き渡す。

## 推奨コマンド
```bash
uv run pptx tpl-extract \
  --template templates/libraries/acme/v1/template.pptx \
  --output .pptx/extract/acme_v1

uv run pptx layout-validate \
  --template templates/libraries/acme/v1/template.pptx \
  --output .pptx/validation/acme_v1 \
  --baseline releases/acme/v0/layouts.jsonl \
  --analyzer-snapshot .pptx/gen/analysis_snapshot.json
```
- `tpl-extract` でレイアウト JSON (`template_spec.json`)・`jobspec.json`・`branding.json` を取得し、`.pptx/extract/<template_id>/` に格納する。
- `layout-validate` で `layouts.jsonl` / `diagnostics.json` / `diff_report.json` を生成し、差分や抽出失敗を検知する。致命的エラーがある場合は exit code 6 を返す。
- `pptx gen --emit-structure-snapshot` で出力された `analysis_snapshot.json` を `--analyzer-snapshot` に渡し、テンプレとレンダリング結果のアンカー整合性を検証する。

## 品質ゲート
- `layouts.jsonl` がスキーマ検証に合格すること。
- プレースホルダ名の重複・欠落が検出された場合はエラー扱い。
- 用途タグとレイアウトカテゴリが未設定の場合は警告として記録。
- 差分レポートが存在しない場合でも、比較対象が無い旨を記録する。
- Analyzer スナップショット突合で `analyzer_anchor_missing` / `analyzer_anchor_unexpected` が発生した場合は対応が完了するまでテンプレを承認しない。

## ログと監査
- 抽出処理時間、レイアウト数、警告件数を `diagnostics.json` に記録する。
- 解析失敗時はテンプレバージョンと原因を必ずログ化する。
- 差分レポートは工程1の `template_release.json` と突合し、変更理由を追跡可能にする。
- Analyzer 突合の警告件数もログ化し、レイアウト配布前レビューで参照できるようにする。

## 未実装項目（機能単位）
- 抽出結果の JSON スキーマ検証 CLI (`extract-template` 拡張)。
- レイアウト差分レポートおよび警告の可視化 UI/レポート出力。
- 面積ベースのヒント係数と用途タグ推定ロジック。
- `analysis_snapshot.json` のスキーマ拡張、および Analyzer とのバージョン整合ポリシー策定。
