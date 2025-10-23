---
目的: RM-036 に基づきドラフト構成インテリジェンス拡張の計画と実装方針を整理し、PoC 対象を特定する
関連ブランチ: feat/rm036-draft-intelligence
関連Issue: #231
roadmap_item: RM-036 ドラフト構成インテリジェンス拡張
---

- [x] ブランチ作成と初期コミット
  - メモ: main から feat/rm036-draft-intelligence を作成。初期コミットで ToDo を登録。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 2025-10-23 ユーザー承認済み。チャット #RM-036 Plan OK を記録。
- [x] 設計・実装方針の確定
  - メモ: 章テンプレ・layout_hint 候補・差戻しテンプレ PoC の構成案を docs/design/stages/stage-04-draft-structuring.md へ反映。
- [x] ドキュメント更新（要件・設計）
  - メモ: 要件・スキーマを更新し、RM-036 の PoC 要件とデータ項目を追加。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: DraftStructuringStep へ章テンプレ/Analyzer/差戻しテンプレ PoC を実装済み。CLI に新オプションを追加。
- [x] テスト・検証
  - メモ: `tests/test_draft_intel.py`, `tests/test_cli_outline.py` を追加し、`UV_CACHE_DIR=.uv-cache uv run --extra dev pytest tests/test_draft_intel.py tests/test_cli_outline.py` と `UV_CACHE_DIR=.uv-cache uv run --extra dev pytest` を実行済み。
- [x] ドキュメント更新
  - メモ: roadmap/design/requirements/runbook/AGENTS を更新し、章テンプレ PoC と CLI 運用手順を反映済み。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: Issue `#231` と連携済み（2025-10-23）。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録し、ワークフロー動作状況も残す。

## メモ
