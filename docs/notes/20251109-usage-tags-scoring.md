# usage_tags スコアリング整理メモ

## 背景
- `uv run pptx template` で抽出した `.pptx/extract/layouts.jsonl` の `usage_tags` が `title` に偏っている事象を確認。
- 生成 AI へ渡す入力としてレイアウト情報を活用するため、タグ付けの意味付けと後続工程での利用方法を整理する。

## usage_tags の抽出ロジック
- Stage1 では `TemplateAIService` を介して生成 AI にレイアウト構造（プレースホルダー種類、テキスト・メディアヒント、ヒューリスティック結果）を渡し、`usage_tags` を返してもらう。  
  実装: `src/pptx_generator/template_ai/service.py`
- AI がタグを返さない場合や未知語のみを返した場合は、従来の `_derive_usage_tags` ヒューリスティックでフォールバックする。  
  実装: `src/pptx_generator/layout_validation/suite.py:320` 付近
- `diagnostics.json` には `template_ai_*` 統計とレイアウト単位の推定結果が記録される。

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
2. フォールバックの維持  
   - `_derive_usage_tags` をフォールバックの基準とし、本文プレースホルダーを持つ汎用レイアウトでは `title` を抑制するなどルールベースの品質を維持する。  
   - AI がタグを返さない／未知語のみの場合は、このフォールバック結果を有効タグとして使用する。
3. バリデーションの強化  
   - `layout_validation` に `usage_tag_title_suppressed` / `usage_tag_unknown` の診断を追加し、CI 上で逸脱を検知する。  
   - タグ語彙の集計値を `diagnostics.json` に残し、テンプレ更新時の差分を追えるようにする。

短期的には **1** で分類結果を主軸に据えつつ、**2** をフォールバックとして活かし、**3** で運用監視を補完する形を目指す。

## 実装状況メモ（2025-11-09）
- `TemplateAIService` を新設し、Stage1 (`pptx template` / `tpl-extract`) で usage_tags を生成 AI へ委譲。ポリシー設定と CLI オプション（`--template-ai-policy` / `--template-ai-policy-id` / `--disable-template-ai`）を追加。
- `layout_validation` で AI 応答を採用しつつ、生成失敗時には従来ヒューリスティックへフォールバック。`diagnostics.json` にテンプレ AI の統計（invoked / success / fallback / failed）とレイアウト単位の推定結果を出力。
- 未知語やエラー時の診断コード（`usage_tag_ai_unknown` / `usage_tag_ai_error` / `usage_tag_ai_fallback`）を追加し、CI で逸脱を検知できるようにした。
- ユニットテスト `tests/test_template_ai.py`（新設）と `tests/test_layout_validation_template_ai.py` で AI 推定およびフォールバックの動作を確認。既存の usage_tags ユーティリティテストも維持。
