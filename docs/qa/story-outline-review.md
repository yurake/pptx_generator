# ストーリー骨子整合チェック結果（2025-10-16）

## 対象
- `docs/requirements/stories/story-outline.md`
- `docs/design/rm005-story-modeler.md`
- `docs/requirements/stages/stage-03-content-normalization.md`
- `docs/requirements/stages/stage-04-draft-structuring.md`
- `docs/runbooks/story-outline-ops.md`

## チェックリスト
- [x] ストーリーフェーズ分類と章メタが requirements / design 間で一致している
- [x] 工程3 出力 (`prepare_card.json`) に必要なストーリー項目が要件として明記されている
- [x] 工程4 の整合チェック手順に `story_outline` との突合が含まれている
- [x] Runbook に運用・ロールバック手順が追加されている
- [x] ToDo から参照できるブランチ情報・ロードマップ番号が更新されている

## 所見
- 現時点で工程3→4 の受け渡し仕様は文書化されている。骨子バージョン差異時のエスカレーションは Runbook へ追記済み。
- `draft_approved.json` 側の詳細スキーマ整理は別タスク（RM-024）に引き継ぐ必要があるため、ToDo メモに追記済み。

## フォローアップ
- 実装タスク着手時に `story_outline.json` のサンプルを `samples/json/` 配下へ追加し、仕様サンプルと紐づける。
- 将来的に工程4 の UI を構築する際は、Runbook のレビュー観点に操作ログ検証を追記する。
