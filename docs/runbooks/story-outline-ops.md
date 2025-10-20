# ストーリー骨子運用手順

## 目的
- RM-005 で定義したストーリー骨子 (`story_outline.json`) を工程3/4で確実に参照し、章構成とストーリーフェーズの整合を維持する。
- HITL 承認者がストーリー情報を確認・更新する際の手順を標準化し、差戻しコストを抑える。

## 事前準備
- `docs/requirements/stories/story-outline.md` と `docs/design/rm005-story-modeler.md` を読み、対象案件で利用すべきフェーズ・章構造とメタ項目を確認する。
- `story_outline.json` のバージョンと発行元 ToDo / Issue を確認し、最新の骨子が共有済みであることを担保する。
- 工程3 要件（`docs/requirements/stages/stage-03-content-normalization.md`）と工程4 要件（`docs/requirements/stages/stage-04-draft-structuring.md`）を参照し、アウトライン項目の受け渡しポイントを把握する。

## 手順
1. ストーリー骨子ファイルをリポジトリに配置し、案件メタと紐づく `title`・`version` を更新する。
2. 工程3 のカード生成設定に骨子ファイルのパスを渡し、`story.phase` / `story.chapter_id` / `story.angle` がカード単位で埋まることを確認する。
3. HITL 承認 API を利用するツール（CLI など）で章・フェーズ表示を確認し、必要に応じて再割当を行う。差分はレビューコメントとして記録する。
4. 承認後の `content_approved.json` を確認し、全カードにストーリー情報が保存されていること、章ごとのスライド数が骨子の想定範囲内であることをチェックする。
5. 工程4 へ引き渡す前に `uv run pptx content ... --output .pptx/content` で承認済みコンテンツを検証し、続けて `uv run pptx outline ... --output .pptx/draft` を実行して章構成・付録設定を確認する。必要に応じて `draft_meta.json` の章統計と `draft_review_log.json` を参照し、齟齬があれば差戻し理由を明示する。最終的に `pptx mapping` → `pptx render` で工程5/6へ進む。

## レビュー観点
- フェーズ必須項目（導入／課題／解決）は欠落していないか。
- 骨子の `default_slide_count` と実際のカード数が大きく乖離していないか。
- 付録送りや統合を行ったスライドの章情報が `draft_review_log.json` と一致しており、章承認後は `locked` が設定されているか。
- ストーリー骨子の更新履歴・レビュー記録が `docs/todo/` や関連 Issue に残っているか。

## ロールバックとエスカレーション
- 骨子に重大な誤りが見つかった場合は、該当 ToDo を差戻しステータスに更新し、承認済みカードを一旦凍結する。
- 調整が間に合わない場合は、直近安定版の `story_outline.json` を復元し、変更理由と影響範囲を `docs/notes/` へ記録する。
- API クライアント側の再割当機能で致命的な不具合が発生した際は、工程3・4 の担当へ即時共有し、暫定措置として骨子メタの手動編集手順を `docs/notes/` に追記する。
