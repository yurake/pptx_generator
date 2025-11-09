---
目的: usage_tags の付与・診断・AI 連携を再設計し、レイアウト選定の整合性を高める
関連ブランチ: feat/rm061-usage-tags-governance
関連Issue: #281
roadmap_item: RM-061 usage_tags ガバナンス強化
---

- [x] ブランチ作成と初期コミット
  - メモ: 2025-11-09 `origin/fix/rm060-stage3-id-enforce` から `feat/rm061-usage-tags-governance` を作成し、ロードマップ／ToDo／調査メモを初期コミット済み（`docs: bootstrap rm061 usage tags governance`）。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: layout_validation の `_derive_usage_tags`、関連スキーマ、Stage3 パイプライン（`draft_structuring.py`、`mapping.py`、`draft_recommender.py`）のタグ利用箇所、及び関連ドキュメント。
    - ドキュメント／コード修正方針: 抽出ロジックを厳格化し、共通タグ正規化ユーティリティを導入。layout_validation にタグ診断を追加し、必要に応じて要件ドキュメントとメモを更新。
    - 確認・共有方法（レビュー、ToDo 更新など）: この ToDo と Plan に沿って進行し、各工程完了時に ToDo 更新。PR で最終共有。
    - 想定影響ファイル: `src/pptx_generator/layout_validation/suite.py`、`schema.py`、`pipeline/draft_structuring.py`、`pipeline/mapping.py`、`draft_recommender.py`、必要な新モジュール、`docs/notes/20251109-usage-tags-scoring.md`、Stage3 関連ドキュメント。
    - リスク: 既存テンプレのスコアリング変動、CI 警告増加。テンプレ抽出結果の確認と警告ガイド整備で対応。
    - テスト方針: 該当ユーティリティの単体テスト追加、テンプレ抽出結果のスナップショット確認、`pytest tests/test_cli_integration.py` で回帰検証。
    - ロールバック方法: `feat/rm061-usage-tags-governance` 内のコミットをリバート／ブランチ破棄で `fix/rm060-stage3-id-enforce` 状態へ戻す。
    - 承認メッセージ ID／リンク: チャットログ (2025-11-09 Plan 承認)
- [x] 設計・実装方針の確定
  - メモ: タグ正規化ユーティリティ導入と layout_validation の警告方針を確定し、Stage3 パイプラインの比較処理にも同ユーティリティを適用する構成で進行。
- [ ] ドキュメント更新（要件・設計）
  - メモ: 
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [x] 実装
  - メモ: `_derive_usage_tags` の改修、`utils/usage_tags.py` 追加、Stage3 パイプラインの正規化実装、CLI 検証スクリプトを整備。
- [x] テスト・検証
  - メモ: `pytest tests/test_utils_usage_tags.py tests/test_layout_validation_usage_tags.py tests/test_template_extraction_script.py`、`pytest tests/test_cli_integration.py`、`bash scripts/test_template_extraction.sh` を実行。
- [x] ドキュメント更新
  - メモ: `docs/notes/20251109-usage-tags-scoring.md` に実装内容を追記。要件／設計ドキュメントの更新は今回対象外。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: Issue 作成後に番号を反映する。
- [ ] PR 作成
  - メモ: 

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
