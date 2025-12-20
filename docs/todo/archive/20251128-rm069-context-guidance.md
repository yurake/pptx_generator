---
目的: RM-069 コンテキスト設計ガイド整備の要求を満たすため、コンテキスト設計ポリシー文書の起草と関連ドキュメント反映の段取りを整える
関連ブランチ: docs/rm069-context-guidance
関連Issue: #332
roadmap_item: RM-069 コンテキスト設計ガイド整備
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ `docs/rm069-context-guidance` を作成し、コミット `docs: add todo for rm069 context policy` を作成済み。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認メッセージ: user msg「ok」(2025-11-28)
    - 対象整理（スコープ、対象ファイル、前提）: コンテキスト設計ポリシーの初版策定と Upfront 文書（README / AGENTS / docs/README）のサマリ化を行い、詳細は下位資料へ誘導する構成へ見直す。既存資料との整合確認を前提とする。
    - ドキュメント／コード修正方針: `docs/policies/context-engineering.md` を新設し、Upfront 文書を要約中心へ再編。Runbook は既存構成に戻し、ToDo テンプレやタスク管理ポリシーは参照リンク記載を明文化する。
    - 確認・共有方法（レビュー、ToDo 更新など）: コミットごとの差分で確認。ToDo メモに進捗を記録し、必要なら `docs/notes/` を共有。
    - 想定影響ファイル: `docs/policies/context-engineering.md`, `README.md`, `AGENTS.md`, `docs/README.md`, 対象 runbook 1 件（候補: `docs/runbooks/story-outline-ops.md`）, `docs/todo/template.md`, 必要に応じて `docs/policies/task-management.md`, `docs/notes/*`
    - リスク: 多数のドキュメント改訂で整合性が崩れる恐れ。既存読者が構成変更で混乱する可能性。参照リンク切れ。
    - テスト方針: コード変更なし。文書の校閲とリンクチェックを手動で実施し、破損リンクが疑われる場合は `rg` 等で検索。
    - ロールバック方法: コミット単位で `git revert`。必要に応じてブランチを破棄し `main` を再チェックアウト。
- [x] 設計・実装方針の確定
  - メモ: Upfront 文書は概要と参照導線だけを残し詳細は下位資料へ委譲する方針へ変更。Runbook は既存構成へ戻し、ToDo テンプレ／タスク管理ポリシーでは参照リンクを必須とする。
- [x] 設計・実装方針メモの共有
  - メモ: `docs/notes/20250214-context-engineering-hand-off.md` に 2025-11-28 更新メモを追加し、実施内容と運用上の留意点を記録した。
- [x] ドキュメント更新（要件・設計）
  - メモ: 今回は要件・設計ドキュメントへの直接変更不要。参照順が既存記述と一致していることを確認済み。
  - [x] docs/requirements 配下
    - メモ: 既存要件文書は従来どおり詳細情報を保持しており、Upfront 文書からの参照導線だけ整備すれば十分と判断。
  - [x] docs/design 配下
    - メモ: 設計文書の参照リンクは変化なし。README からのリンク先も現状のままで問題ないことを確認。
- [x] 実装
  - メモ: `docs/policies/context-engineering.md` を整備し、README / AGENTS / docs README をサマリ中心へ改稿。Runbook を元の構成へ復元し、ToDo テンプレートとタスク管理ポリシーを参照リンク必須とする内容に更新。
- [x] テスト・検証
  - メモ: コード変更なし。`rg` で不要な用語が残っていないか確認し、文書リンクを目視で点検した。
- [x] ドキュメント更新
  - メモ: 関連カテゴリの更新状況を整理し、未更新カテゴリについては理由を記載。
  - [x] docs/roadmap 配下
    - メモ: RM-069 の期待成果と整合しており追加更新不要。
  - [x] docs/requirements 配下（実装結果との整合再確認）
    - メモ: 既存要件は参照リンク追加のみで影響なし。
  - [x] docs/design 配下（実装結果との整合再確認）
    - メモ: 設計ドキュメント側でコンテキスト構成の補足不要。
  - [x] docs/runbook 配下
    - メモ: `docs/runbooks/story-outline-ops.md` を従来構成へ戻し、参照導線のみ整備。
  - [x] README.md / AGENTS.md
    - メモ: Upfront 文書を要約＋参照リンクのみの構成へ刷新した。
- [x] 関連Issue 行の更新
  - メモ: #332 を参照し、ToDo フロントマターを更新済み。
- [x] チェックリスト整合確認
  - メモ: 全チェック項目に対応し、親子関係の整合も確認済み。PR 作成待ち。
- [x] PR 作成
  - メモ: PR #333 https://github.com/yurake/pptx_generator/pull/333（2025-11-28 完了）

## メモ
- 2025-11-29: `docs/design/` を CLI / architecture / archive / stages へ整理し、関連ドキュメントの参照リンクを最新構成へ更新済み。
