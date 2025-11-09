# usage_tags スコアリング整理メモ

## 背景
- `uv run pptx template` で抽出した `.pptx/extract/layouts.jsonl` の `usage_tags` が `title` に偏っている事象を確認。
- 生成 AI へ渡す入力としてレイアウト情報を活用するため、タグ付けの意味付けと後続工程での利用方法を整理する。

## usage_tags の抽出ロジック
- 実装: `src/pptx_generator/layout_validation/suite.py:520` 付近の `_derive_usage_tags`。
- ルール:
  - レイアウト名に `title` / `cover` が含まれると `title`、`agenda` / `toc` で `agenda`、`summary` / `overview` で `overview` などを付与。
  - プレースホルダー種別が `chart` / `table` / `image` / `title` / `body` の場合に、それぞれ `chart` / `table` / `visual` / `title` / `content` を追加。
- 結果: タイトル型プレースホルダーを 1 つ含むだけで `title` タグが付与されるため、汎用レイアウトでも `title` が混入する。

## usage_tags の利用箇所
- 工程3 ドラフト構築: `src/pptx_generator/pipeline/draft_structuring.py:282` 付近。
  - `layout_candidates` 生成時に `intent` 一致で `+0.4`、`type_hint` 一致で `+0.3` を加点。
  - `text_hint.max_lines` やテーブル可否で追加の加減点。
- 工程5 マッピング: `src/pptx_generator/pipeline/mapping.py:353` 付近。
  - `intent` 一致で `+0.5`、`type_hint` 一致で `+0.15` を加点。
  - 上限行数、テーブル可否、直前レイアウト重複などで補正。
- `fix/rm060-stage3-id-enforce` ブランチのレコメンダ: `src/pptx_generator/draft_recommender.py:136` 付近。
  - 同じ完全一致判定で `intent` に `+0.4`、`type_hint` に `+0.25`。
  - スライド本文から抽出したトークンとの重複で最大 `+0.15` ボーナス。
  - 生成 AI (LayoutAI) は候補への加点を行うが、タグの意味基準はヒューリスティックの完全一致を前提。

## 課題
- 「タイトルプレースホルダーを持つ汎用レイアウト」が `title` タグを持ち、実際の意図が `content` でも `title` と判定されうる。
- `usage_tags` は `intent` / `type_hint` と完全一致したときのみスコアが入るため、自由語彙のタグを与えてもレコメンド精度は向上しない。

## 示唆・今後の検討
- `_derive_usage_tags` のルールを見直し、プレースホルダー型だけでは `title` を付けない等の抑制が必要。
- 生成 AI でレイアウト分類を行う場合でも、最終的に `intent` / `type_hint` と整合する語彙へ正規化する仕組みが求められる。
- レイアウトレビュー時に `usage_tags` を点検し、タイトル用途のレイアウトに限定して `title` を設定する運用を検討する。

## 対応案の方向性
1. 抽出ロジックの改修
   - `_derive_usage_tags` に「タイトル型プレースホルダーが 1 つだけ存在し、`body` がある場合は `title` を付けない」などの条件を追加する。
   - 併せて `layout_name` のパターン判定を強化し、`title` 判定には `title` / `cover` など特定語を厳密に要求する。
3. 生成 AI による分類の活用
   - AI が出力した分類をテンプレート内の `layout_id` 単位で正規化（例: `primary-title` → `title`）する辞書を用意し、スコアリングと整合する語彙に変換する。
   - AI 結果はログに残し、差異が大きい場合に人手確認へ回す運用とする。
4. バリデーションの強化
   - `layout_validation` に、`title` タグの付与条件を満たしているかを診断するルールを追加し、`title` タグ過剰時には警告を出す。
   - CI で `usage_tags` の語彙セットをチェックし、未知タグの混入や `title` 過多を検出する。

短期的には **1**（抽出ロジック改修）と **4**（バリデーション強化）を優先し、`title` タグの過剰付与を構造的に抑止する。生成 AI を使う場合は **3** の正規化を前提条件とし、語彙の統一を担保する。
