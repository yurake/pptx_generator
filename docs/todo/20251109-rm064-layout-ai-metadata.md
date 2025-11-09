---
目的: layout_ai 応答へテンプレ構造メタ情報を渡し、AI 推薦とスコアリングの整合性を高める
関連ブランチ: feat/rm064-layout-ai-metadata
関連Issue: #281
roadmap_item: RM-064 レイアウト候補メタ情報拡充
---

- [x] ブランチ作成と初期コミット
  - メモ: 2025-11-09 `main` から `feat/rm064-layout-ai-metadata` を作成し、`docs(todo): bootstrap rm061 usage tags governance` 初期コミットを引き継ぎ。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: Stage3 `CardLayoutRecommender` を起点に `layout_ai/client.py` と `draft_structuring` でやり取りするレイアウト候補メタデータを拡張し、AI 推薦時に usage_tags を正規化して利用できるようにする。既存オブジェクトを拡張し、新規 JSON は増やさない。
    - ドキュメント／コード修正方針: `LayoutAIRequest` の payload にテンプレ構造メタデータを添付し、AI 応答から得たタグを `normalize_usage_tags_with_unknown` で正規化。AI がタグを返さない場合は従来の usage_tags をフォールバックとして利用する。`mapping_log` に AI タグ／フォールバックタグを記録して差分を可視化する。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo を都度更新し、進捗は PR で共有。必要に応じて `docs/notes` に補足メモを追加。
    - 想定影響ファイル: `src/pptx_generator/draft_recommender.py`, `src/pptx_generator/layout_ai/client.py`, `src/pptx_generator/pipeline/draft_structuring.py`, `docs/notes/20251109-usage-tags-scoring.md`, `tests/test_layout_recommender.py` など。
    - リスク: AI 応答フォーマット揺らぎによるタグ抽出失敗、メタ情報増加に伴うレスポンス遅延、既存 usage_tags との不整合。フォールバックとログで影響可視化し、必要時に手動確認。
    - テスト方針: ユニットテストでタグ正規化とフォールバック経路を確認し、`tests/test_cli_integration.py` で工程全体の回帰を確認。必要に応じて `uv run pptx tpl-extract` でメタデータ出力を検証。
    - ロールバック方法: `feat/rm064-layout-ai-metadata` のコミットをリバートし、AI メタデータ拡張を無効化する。
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
- [ ] layout_ai policy の拡張検討
  - メモ: 既存 policy JSON の構造と prompt 設計を見直し、メタデータ活用方針を整理する。
- [ ] Stage1 メタデータ抽出強化の検討
  - メモ: `pptx template` でのプレースホルダー要約や AI 連携可否を洗い出し、Stage3 と連携するための差分をまとめる。
- [ ] CLI / ログ / テスト整備
  - メモ: 新しいメタデータを利用する CLI オプションやログ項目を定義し、必要な統合テスト追加を検討する。
- [x] 関連Issue 行の更新
  - メモ: 
- [ ] PR 作成
  - メモ: 

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
