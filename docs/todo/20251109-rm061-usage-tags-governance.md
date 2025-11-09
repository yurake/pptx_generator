---
目的: usage_tags の付与・利用をガバナンスし、レイアウト意図と intent/type_hint の一致具合を安定させる
関連ブランチ: feat/rm061-usage-tags-governance
関連Issue: #281
roadmap_item: RM-061 usage_tags ガバナンス強化
---

- [x] ブランチ作成と初期コミット
  - メモ: 2025-11-09 `main` から `feat/rm061-usage-tags-governance` を作成し、`docs(todo): bootstrap rm061 usage tags governance` で本 ToDo を追加する初期コミットを実施済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: Stage3 `CardLayoutRecommender` を起点に、`layout_ai/client.py` と `draft_structuring` でやり取りするレイアウトメタ情報を拡張し、AI から受け取る分類結果を `usage_tags` へ正規化して活用する仕組みに切り替える。既存 JSON／モデルを拡張し、追加ファイルは作成しない。
    - ドキュメント／コード修正方針: `LayoutAIRequest` の payload にレイアウトメタデータを添付し、AI 応答から得たタグを `normalize_usage_tags_with_unknown` で正規化。AI がタグを返さない場合は従来の `_derive_usage_tags` 由来タグをフォールバックとして利用する。ログと `diagnostics` に分類結果と差分を残し、`docs/notes/20251109-usage-tags-scoring.md` に運用手順を追記する。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo の進捗更新、必要に応じて追加メモを `docs/notes` へ記載。最終的に PR で差分とログ整備を共有する。
    - 想定影響ファイル: `src/pptx_generator/draft_recommender.py`, `src/pptx_generator/layout_ai/client.py`, `src/pptx_generator/pipeline/draft_structuring.py`, `src/pptx_generator/utils/usage_tags.py`, `docs/notes/20251109-usage-tags-scoring.md`, 付随テスト。
    - リスク: AI 応答フォーマットの揺らぎでタグ抽出に失敗する可能性、メタ情報増加によるリクエスト肥大化、既存テンプレートでタグが変化しスコアリングが揺れるリスク。フォールバック処理とログ出力で影響を可視化する。
    - テスト方針: ユニットテストでタグ正規化とフォールバックを検証し、`tests/test_cli_integration.py` で工程3が破綻しないことを確認。必要に応じて `uv run pptx tpl-extract` で手動確認。
    - ロールバック方法: `feat/rm061-usage-tags-governance` の対象コミットを順にリバートし、AI 連携を無効化して従来ロジックへ戻す。
    - 承認メッセージ ID／リンク: チャットログ（2025-11-09 Plan 承認）
- [x] 設計・実装方針の確定
  - メモ: AI から受け取るタグを canonical 語彙へ正規化し、未知語はフォールバックとして既存 `usage_tags` を利用する二段構えで進める。レイアウトメタデータ（プレースホルダー要約・text/media ヒント）を `LayoutAIRequest` に添付し、分類根拠を `mapping_log` に記録する設計を採用。
- [ ] ドキュメント更新（要件・設計）
  - メモ: 
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [x] 実装
  - メモ: `CardLayoutRecommender` の AI リクエスト拡張、分類結果の正規化とフォールバック、`layout_ai/client.py` のスキーマ／パーサ更新、`draft_structuring` のプレースホルダー要約生成とログ拡張を完了。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_layout_recommender.py tests/test_utils_usage_tags.py tests/test_layout_validation_usage_tags.py` を実行し、分類の上書きと正規化の挙動を確認。
- [x] ドキュメント更新
  - メモ: `docs/notes/20251109-usage-tags-scoring.md` に AI 主体の分類フローとフォールバック方針を追記。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
