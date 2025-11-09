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
1. 生成 AI による分類の活用  
   - レイアウトごとのプレースホルダー構成・テキスト／メディア収容力をメタデータとして AI へ渡し、`allowed_tags` を明示した上で分類タグを返してもらう。  
   - 応答のタグは `layout_id` 単位で正規化し、未知語が残った場合でも差分をログ化して人手確認へ回せるようにする。
2. 抽出ロジックの改修  
   - `_derive_usage_tags` をフォールバックの基準とし、本文プレースホルダーを持つ汎用レイアウトでは `title` を抑制するなどルールベースの品質を維持する。  
   - AI がタグを返さない／未知語のみの場合は、このフォールバック結果を有効タグとして使用する。
3. バリデーションの強化  
   - `layout_validation` に `usage_tag_title_suppressed` / `usage_tag_unknown` の診断を追加し、CI 上で逸脱を検知する。  
   - タグ語彙の集計値を `diagnostics.json` に残し、テンプレ更新時の差分を追えるようにする。

短期的には **1** で分類結果を主軸に据えつつ、**2** をフォールバックとして活かし、**3** で運用監視を補完する形を目指す。

## 実装状況メモ（2025-11-09）
- `_derive_usage_tags` をリファクタリングし、本文プレースホルダーが存在するレイアウトでは `title` タグを付与しないよう調整。レイアウト名が「Title and Content」のようなケースを除外しつつ、表紙・セクション系は維持。
- `layout_validation` で `usage_tag_title_suppressed` / `usage_tag_unknown` 警告を出せるようにし、未知タグは正規化時に除外して警告のみ記録。
- `pptx_generator/utils/usage_tags.py` を追加し、タグ正規化ユーティリティとシノニムマップを定義。`mapping` / `draft_structuring` / `draft_recommender` で共通利用し、`intent`・`type_hint`・AI 出力を同じ語彙に揃える。
- `CardLayoutRecommender` から AI へ送る payload にレイアウトメタデータ（プレースホルダー要約、text/media ヒント、許容タグ）を添付し、応答に含まれるタグを `normalize_usage_tags_with_unknown` で正規化して採用する仕組みを導入。未知語は `ai_unknown_tags` としてログ／診断に残す。
- 単体テスト (`tests/test_utils_usage_tags.py`, `tests/test_layout_validation_usage_tags.py`, `tests/test_layout_recommender.py`) を更新し、AI タグの正規化とフォールバック挙動を検証する。
