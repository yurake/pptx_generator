# 工程5 マッピング 要件詳細

## 概要
- 承認済みドラフトとテンプレ構造を統合し、レンダリング準備 JSON を生成する。
- ルールベースと AI 補完を組み合わせ、プレースホルダへの要素割付を完了させる。

## 入力
- `draft_approved.json`: 章構成、スライド順、`layout_hint`。
- `prepare_card.json`: 章・メッセージ・意図タグを含むブリーフカード。
- `layouts.jsonl`, `diagnostics.json`: レイアウト構造と警告情報。

## 出力
- `generate_ready.json`: スライドごとの `layout_id`、PH → 要素マッピング、メタ情報（`job_meta` / `job_auth` を含む）。
- `mapping_log.json`: スコアリング結果、AI 補完箇所、フォールバック履歴、Analyzer 指摘サマリ（件数集計とスライド別一覧）。
- 失敗レポート: 未割付要素や収容不能スライドの一覧。

## ワークフロー
1. レイアウト候補を用途タグと必須要素でフィルタし、スコアリングを実施する。
2. ルールベースで一次割付を行い、空要素を抽出する。
3. AI 補完で未割付や冗長要素を再配分し、必要に応じてスライド分割・縮約を行う。
4. フォールバックルール（縮約 → 分割 → 付録）を適用し、その履歴を記録する。
5. JSON スキーマ検証を通過した `generate_ready.json` を出力し、工程6へ送る。

## 品質ゲート
- 全スライドが `layout_id` を持ち、必須 PH が埋まっている。
- `generate_ready.json` がスキーマ検証を通過し、空要素は意図的であるとログに記載される。
- フォールバック適用時に理由が `mapping_log.json` に記録されている。
- Analyzer 指摘が `mapping_log.json` のメタ（件数サマリ）およびスライド単位サマリに反映され、後続工程で参照できる。
- AI 補完結果が監査ログに明示され、後追い確認が可能である。
- フォールバックが発生した場合は `fallback_report.json` を併産し、該当スライドと理由を一覧化する。

## ログ・監査
- 候補レイアウトのスコア（必須充足・容量適合・用途タグ・多様性）を保持する。
- AI 補完前後の差分を記録し、自動修正率を算出できるようにする。
- 収容不能ケースはエラー扱いとし、再実行のためのチェックリストを添付する。
- 監査ログ (`audit_log.json`) で `generate_ready`・`mapping_log` の SHA-256 を収集し、`mapping_meta` にスライド数・フォールバック対象 ID・生成時刻を記録してトレーサビリティを確保する。

## 未実装項目（機能単位）
- レイアウトスコアリングとフォールバック制御ロジック。
- AI 補完の差分記録と監査ログ連携。
- `generate_ready.json` スキーマ検証ツールと失敗時ガイド生成。

## 実装メモ
- 2025-10-21 時点では、`shrink_text` フォールバック（本文行数の縮約）をルールベースで提供し、その結果を JSON Patch 形式で `mapping_log.json` に記録する。AI モデル連携は将来拡張予定。
- Analyzer は工程6で走査した結果を再度 `mapping_log.json` に書き戻し、フォールバック履歴と合わせて可観測性を確保する。
- `layouts.jsonl` が未指定の場合はドラフト情報を自動補完し、スコアリングはヒューリスティックに実行する。
- 生成物は `generate_ready.json`、`mapping_log.json`、必要に応じて `fallback_report.json` を CLI 出力ディレクトリ直下へ保存する。
- CLI では `uv run pptx mapping <spec.json> --brief-cards .pptx/prepare/prepare_card.json --brief-log .pptx/prepare/brief_log.json` が工程5の実行パスであり、`pptx gen` 実行時もこのコマンドを内部的に呼び出す。
