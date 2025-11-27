---
目的: RM-077 LLM ラベル整備
関連ブランチ: feat/rm077-llm-enhancements
関連Issue: #316
roadmap_item: RM-077 LLM ラベル整備
---

- [x] ブランチ作成・初期コミット・push
  - メモ: main から feat/rm077-llm-enhancements を作成し、`docs: add todo for rm077 llm enhancements` をコミット済み。リモートへは push 未実施。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: `.github/issue-labeler.yml` / `.github/labeler.yml` に `area:llm` を追加し、`docs/policies/github-label-governance.md` で運用ルールを更新する。LLM 関連ディレクトリとキーワード定義を整理し、既存ラベルとの整合を保つ。
    - ドキュメント／コード修正方針: ラベルポリシーに表とルールを追記し、Issue/PR 自動付与設定へパターンを追加。設定変更は YAML フォーマットを崩さないよう手動編集し、必要に応じて `yq` / `jq` で検証する。
    - 確認・共有方法（レビュー、ToDo 更新など）: 変更内容はこの ToDo と `docs/roadmap/roadmap.md` の RM-077 セクションに記録し、PR 説明にも `area:llm` 追加の背景を記載する。
    - 想定影響ファイル: `.github/issue-labeler.yml`, `.github/labeler.yml`, `docs/policies/github-label-governance.md`, `docs/roadmap/roadmap.md`（状況更新のみ）。
    - リスク: 正規表現やグロブ誤設定による誤ラベル付与。既存ワークフローが失敗する可能性。導入直後は対象 PR/Issue で結果を確認し、誤りがあれば即時修正する。
    - テスト方針: `yamllint` 相当のチェックは手元にないため、`python -m compileall` 同等の構文検査は行わず `yq` で読み込み確認する。必要に応じて `act` で `labeler` ワークフローのドライランを実施する。
    - ロールバック方法: 追加した `area:llm` 行を削除して元の YAML を復元し、ポリシードキュメントの該当セクションを revert する。
    - 承認メッセージ ID／リンク: ユーザー承認「ok」（2025-11-24 の会話メッセージ）を参照。
- [x] 設計・実装方針の確定
  - メモ: 自動ラベルの対象に `prepare` / `content_ai` / `layout_ai` / `template_ai` / LLM 補助ステップ（`pipeline/slide_alignment.py`、`draft_recommender.py`）を含め、ポリシー／設定ファイル一式をカバーする方針で確定。既存エリアラベルと重複した場合はレビューで調整する。
- [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - メモ: 追加ドキュメント不要と判断。判断者: Assistant（2025-11-24）。再検討条件: LLM 対象領域が増えた際に改めて記録。
- [x] ドキュメント更新（要件・設計）
  - メモ: `docs/policies/github-label-governance.md` と `docs/roadmap/roadmap.md` を更新済み。変更不要の領域については以下に記録。
  - [x] docs/requirements 配下
    - メモ: ラベル運用変更による要件影響なしのため更新不要。
  - [x] docs/design 配下
    - メモ: 設計ドキュメントへの影響なしのため更新不要。
- [x] 実装
  - メモ: `.github/issue-labeler.yml` / `.github/labeler.yml` に `area:llm` を追加し、対象パスとキーワードを反映。
- [x] テスト・検証
  - メモ: `uv run python - <<'PY' ...` により `.github/issue-labeler.yml` / `.github/labeler.yml` を `yaml.safe_load` で検証し、`yaml-ok` を確認。
- [x] ドキュメント更新
  - メモ: ラベルポリシーとロードマップへ RM-077 追加済み。その他領域は影響なし。
  - [x] docs/roadmap 配下
    - メモ: RM-077 セクションを追加。
  - [x] docs/requirements 配下（実装結果との整合再確認）
    - メモ: ラベル整備は要件文書へ影響なし。
  - [x] docs/design 配下（実装結果との整合再確認）
    - メモ: 設計ドキュメントへの影響なし。
  - [x] docs/runbook 配下
    - メモ: 運用手順影響は現時点でなし。
  - [x] README.md / AGENTS.md
    - メモ: 表記変更不要のため更新せず。
- [x] 関連Issue 行の更新
  - メモ:
- [x] チェックリスト整合確認
  - メモ: PR 作成を除く stage が完了していることを確認。
- [x] PR 作成
  - メモ: PR #322 https://github.com/yurake/pptx_generator/pull/322（2025-11-26 完了）

## メモ
