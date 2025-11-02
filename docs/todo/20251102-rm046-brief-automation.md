---
目的: RM-046 生成AIブリーフ構成自動化の要件確認と実装準備を進め、段階的な deliverable を定義する
関連ブランチ: feat/rm046-brief-automation
関連Issue: #252
roadmap_item: RM-046 生成AIブリーフ構成自動化
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/rm046-brief-automation を main から作成し、`docs(todo): add rm046 kickoff todo` を初期コミットとして登録済み。
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）
    - ドキュメント／コード修正方針
    - 確認・共有方法（レビュー、ToDo 更新など）
    - 想定影響ファイル
    - リスク
    - テスト方針
    - ロールバック方法
    - 承認メッセージ ID／リンク
    - Plan承認: ユーザー「ok」（2025-11-02 02:11 JST）
    - スコープ: RM-046「生成AIブリーフ構成自動化」の最終形に合わせて工程3の仕様を再設計し、現行設計との差分を整理する。既存挙動の互換維持は考慮せず、理想像への刷新を前提とする。
    - 影響ファイル: docs/requirements/stages/stage-03-content-normalization.md, docs/design/stages/stage-03-content-normalization.md, 必要に応じて docs/notes/, docs/roadmap/roadmap.md。
    - 前提・確認: 生成AIモード周辺（config/content_ai_policies.json, src/pptx_generator/content_ai/ など）の現状を把握し、RM-046 の期待成果（テンプレ依存ゼロの抽象ブリーフカード、HITL ログ方針）に照らして不足点を特定する。
    - 手順:
      1. 関連ドキュメント・コードから現状の生成AIフローと制約を洗い出し、RM-046 のゴールとギャップを一覧化する。
      2. ブリーフ入力フォーマット、生成カード構造、HITL ログ／承認フローの改訂案をまとめ、更新するドキュメント章立てを設計する。
      3. 了承後に進めるドキュメント改訂作業と、将来の実装タスク・検証方針・ロールバックシナリオを明文化する。
    - リスク: 他工程との整合（特に RM-047 以降）や未確定仕様の扱いが曖昧になること。保留事項はメモ化し次アクションを明確化する。
    - テスト方針: 本フェーズは仕様更新のみでテスト実施なし。実装フェーズで `uv run --extra dev pytest` 等を走らせる前提をドキュメントに記載する。
    - ロールバック: 変更ドキュメントを `git revert` で戻すか、差分を `git checkout` する。
- [x] 設計・実装方針の確定
  - メモ: `docs/notes/20251102-rm046-brief-analysis.md` に BriefCard への全面移行と実装ロードマップ／検証方針を整理済み。
- [x] ドキュメント更新（要件・設計）
  - メモ: 要件・設計の合意内容を整理し、迷う点はユーザーへ相談した結果を残す
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: Brief 正規化パイプライン（`src/pptx_generator/brief/*`, `pipeline/brief_normalization.py`）および CLI 更新を実装済み。API のブリーフストア追加、テストの更新（`tests/test_cli_*` 等）も適用済み。今後の残タスクは RM-046 実装範囲に従って別途管理。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest` を実行し 156 テスト通過。主要 CLI テスト（brief 入力、PDF、compose など）も緑化済み。
- [ ] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
- 実装・テストは当コミットで完了済み。残課題としてドキュメント更新（README, roadmap 等）を別タスクで行う。
