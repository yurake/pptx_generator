---
目的: RM-075 GitHub ラベル運用整備
関連ブランチ: docs/rm075-github-label-governance
関連Issue: #311
roadmap_item: RM-075 GitHub ラベル運用整備
---

- [x] ブランチ作成・初期コミット・push
  - メモ: `main` から `docs/rm075-github-label-governance` を作成。初期コミットは Plan 承認後に実施予定のため未実施。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan を転記する。
    - 対象整理（スコープ、対象ファイル、前提）: 既存ラベル棚卸しと命名規約整備、Issue/PR へ `github/issue-labeler` と `actions/labeler` を導入、運用ガイドを `docs/policies/` に追記。`todo-sync` 既存自動化との整合を維持する。
    - ドキュメント／コード修正方針: ポリシードキュメント新設、ロードマップと README のリンク更新。GitHub Actions ワークフロー・設定ファイルを追加し、Issue テンプレートの初期ラベルを統一する。
    - 確認・共有方法（レビュー、ToDo 更新など）: Plan は本 ToDo とリポジトリ更新で共有。実装後に ToDo を更新し、PR で運用手順と検証ポイントを説明。
    - 想定影響ファイル: `.github/issue-labeler.yml`, `.github/labeler.yml`, `.github/workflows/issue-labeler.yml`, `.github/workflows/pr-labeler.yml`, `.github/ISSUE_TEMPLATE/*.yml`, `docs/policies/github-label-governance.md`, `docs/README.md`, `docs/roadmap/roadmap.md`, `docs/todo/20251124-github-label-governance.md`。
    - リスク: 自動付与の誤検知、既存 Issue/PR へのラベル付け漏れ、`todo-sync` など既存自動化との衝突、ラベル改称に伴う履歴参照の混乱。
    - テスト方針: `uv run python` で YAML 構文チェック。GitHub 上ではワークフローの `workflow_dispatch` を利用して検証し、サンプル Issue/PR で実挙動を確認予定。
    - ロールバック方法: 追加したワークフローと設定ファイルを削除し、Issue テンプレートやドキュメントを以前の命名へ戻す。必要に応じて Git 履歴から復元。
    - 承認メッセージ ID／リンク: ユーザー返信「ok」（2025-11-24）
- [x] 設計・実装方針の確定
  - メモ: ラベル分類と自動付与ルールを `docs/policies/github-label-governance.md` に整理し、Issue テンプレートは `type:` 命名に統一。Issue はタイトル・本文キーワードで、PR は変更ファイルでラベルを付与する。既存 `todo-sync` ラベルは互換維持し、ステータス・優先度ラベルは手動運用とする。
- [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - メモ: 設計内容は `docs/policies/github-label-governance.md` に集約。追加ノートは不要。
- [x] ドキュメント更新（要件・設計）
  - メモ: 要件・設計文書へ変更不要。ラベル運用はポリシードキュメントで管理するため、現時点で仕様変更は発生しない。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: ラベル設定ファイル・GitHub Actions ワークフローを追加し、Issue テンプレートの初期ラベルを `type:` 系へ統一。
- [x] テスト・検証
  - メモ: `uv run python` で `.github/issue-labeler.yml` と `.github/labeler.yml` の YAML 構文を確認。GitHub Actions 手動実行時は `issue-labeler` / `pr-labeler` ともに対象番号入力が必要なため、`workflow_dispatch` に必須入力を追加済み。
- [x] ドキュメント更新
  - メモ: `docs/policies/github-label-governance.md` を新設し、`docs/README.md` と `docs/roadmap/roadmap.md` を更新。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
    - メモ: ラベル運用は要件定義に影響なし。更新不要を確認。
  - [x] docs/design 配下（実装結果との整合再確認）
    - メモ: 設計文書に追記不要。ポリシー側で管理。
  - [x] docs/runbook 配下
    - メモ: 運用手順への反映は不要なため未更新。
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 対応する Issue 未作成。必要になれば # 番号を更新する。
- [x] チェックリスト整合確認
  - メモ: 未着手項目は `関連Issue` と `PR 作成` のみであり、今後のフローに合わせて残置。
- [x] PR 作成
  - メモ: PR #312 https://github.com/yurake/pptx_generator/pull/312（2025-11-24 完了）

## メモ
