# ストーリー骨子運用手順

## 目的
- RM-005 で定義したストーリー骨子 (`story_outline.json`) を stage 3/4 で確実に参照し、章構成とフェーズの整合を維持する。
- HITL 承認者がストーリー情報を確認・更新する際の手順を標準化し、差戻しコストを抑える。

## 事前準備
- 仕様把握: `docs/requirements/stages/stage-02-prepare.md`、`docs/requirements/stages/stage-03-compose.md`、`docs/requirements/stages/stage-04-gen.md` と設計メモ `docs/design/stages/stage-03-story-modeler.md` を確認し、骨子メタの流れを把握する。
- アセット確認: `story_outline.json` をリポジトリ内（または案件共有ストレージ）に配置し、`title`・`version`・発行元 ToDo / Issue を最新化しておく。
- 入力前チェック: stage 2 のカード生成設定に骨子パスが渡せる状態か確認し、`prepare_card.json` のサンプルで `story.phase` / `story.chapter_id` / `story.angle` などが付与されていることを確かめる。

## 手順
1. **骨子の適用**  
   `story_outline.json` を stage 2 のカード生成処理に指定し、`prepare_card.json`・`prepare_story_outline.json` へストーリーメタが反映されているか確認する。骨子の章数・フェーズ数とカード枚数が著しく乖離している場合は、生成前に骨子を見直す。
2. **HITL レビュー**  
   承認ツール（CLI や UI）で章・フェーズ情報を表示し、再割当が必要な場合は `prepare_card.json.cards[*].story` を更新する。差戻し理由や再割当ログは ToDo／ノートに残す。
3. **Compose 実行**  
   Stage 3/4 の再構成は `uv run pptx compose <jobspec.json> --prepare-cards .pptx/prepare/prepare_card.json --output .pptx/compose` を使用する（ドラフト成果物は `.pptx/compose/draft` に自動配置される）。実行後に以下を確認する:
   - `.pptx/compose/draft/draft_review_log.json` に章ごとの承認履歴が残っている。
   - `.pptx/compose/draft/generate_ready_meta.json.sections[*].story_phase` と `status` が骨子と一致している。
   - `DraftStructuringError` が発生した場合はメッセージに記載されたカード ID を `prepare_card.json` と照合し、欠番や重複がないか見直す。
4. **成果物の整合チェック**  
   `generate_ready.json` のスライド順と `story.phase` の整合を確認し、必要に応じて `draft_mapping_log.json` の `fallback` / `slot_checks` / `layout_hint` 情報を参照する。付録送りや統合が発生した場合は `generate_ready_meta.sections[*].fallback_reason` で骨子との齟齬を確認し、差戻しを検討する。
5. **レンダリング前の最終確認**  
   `.pptx/gen/audit_log.json.mapping` に `generate_ready` と `draft_mapping_log` の SHA-256 が記録されているかをチェックし、骨子バージョンや ToDo 番号を `mapping_meta.story_outline` （未実装の場合はメモ欄）に記録する。

## レビュー観点
- フェーズ必須項目（導入／課題／解決など）が欠落していないか。
- `story_outline.json` の `default_slide_count` と実際のカード数の差が許容範囲か。
- 付録送り・統合を行ったスライドの章情報が `draft_review_log.json` と `generate_ready_meta.sections[*]` に反映されているか。
- 骨子の更新履歴・レビュー記録が ToDo や関連ノートに残っているか。

## ロールバックとエスカレーション
- 骨子に重大な誤りが見つかった場合は、該当 ToDo を差戻しステータスに更新し、承認済みカードを凍結する。
- 緊急で元に戻す場合は直近安定版の `story_outline.json` を復元し、再適用後に Compose を再実行する。
- 再割当機能に不具合が発生した場合は stage 3/4 の担当へ連絡し、暫定措置として `prepare_card.json` の手動編集手順をノートに追記する。
