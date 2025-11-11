---
目的: 工程3のレイアウトAI応答で得られるトップ候補を即採用できるようにし、従来のスコア合成処理を省略する
関連ブランチ: feat/rm054-static-blueprint-plan
関連Issue: 未作成
roadmap_item: RM-054 静的テンプレ構成統合
---

- [x] ブランチ作成と初期コミット
  - メモ: 既存ブランチ `feat/rm054-static-blueprint-plan` を継続利用する（初期セットアップ済み）
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認メッセージ(2025-11-12 "ok")を受領。Plan を以下の通り転記。
    - 対象整理（スコープ、対象ファイル、前提）: 工程3のレイアウト候補決定ロジックを対象とし、AI応答が得られたスライドで従来のスコア合成を省いてトップ候補を即採用する。フォールバック用途としてヒューリスティック／シミュレーションは保持する。想定変更ファイルは `src/pptx_generator/draft_recommender.py` と `tests/test_layout_recommender.py`。
    - ドキュメント／コード修正方針: `CardLayoutRecommender.recommend` と `_apply_layout_ai` の分岐を調整し、AI応答成功時はトップ候補のみを `RecommendationResult` へ反映。AIレスポンスが空・解析失敗・モックプロバイダーの場合は従来ロジック（ヒューリスティック合成）を利用。必要に応じてログやAIメタ情報の整合も確認。
    - 確認・共有方法（レビュー、ToDo 更新など）: 作業完了時に当該 ToDo を更新し、ユーザーへ結果報告。必要に応じて関連ドキュメントやメモを連絡。
    - 想定影響ファイル: `src/pptx_generator/draft_recommender.py`, `tests/test_layout_recommender.py`。
    - リスク: AI応答のJSON形式が想定外の場合に候補ゼロとなる可能性、従来のログ・メタ情報が欠落する可能性。例外時フォールバックの確実な維持が必要。
    - テスト方針: `uv run --extra dev pytest tests/test_layout_recommender.py` を実行し、AI成功／失敗ケース双方の挙動を確認。必要ならテストを追加。
    - ロールバック方法: `draft_recommender.py` と関連テストの変更を `git revert` することで従来のスコア合成ロジックへ戻す。
    - 承認メッセージ ID／リンク: ユーザー承認 (2025-11-12, メッセージ "ok")
- [x] 設計・実装方針の確定
  - メモ: AI応答トップ1のみ採用する方針とフォールバック維持を実装に反映済み、追加検討事項なし。
- [x] ドキュメント更新（要件・設計）
  - メモ: 本対応はコード内の挙動調整のみで、既存設計ドキュメントの記述変更は不要と判断。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `CardLayoutRecommender` の AI 応答処理を更新し、トップ候補のみを採用するロジックへ変更。`layout_ai` のプロンプトにも単一候補指示を追加。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_layout_recommender.py`
- [x] ドキュメント更新
  - メモ: 影響範囲を確認し、追加更新は不要。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 該当Issue未作成のため `未作成` 表記を維持、現状共有済み。
- [ ] PR 作成
  - メモ: 

## メモ
