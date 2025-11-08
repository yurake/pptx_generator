---
目的: Stage3 ドラフト構成で JobSpec と BriefCard のスライド ID 不整合を即時検知し、処理を停止する品質ゲートを導入する
関連ブランチ: fix/rm060-stage3-id-enforce
関連Issue: #276
roadmap_item: RM-060 Stage3 ID 整合性強制
---

- [x] ブランチ作成と初期コミット
  - メモ: fix/rm060-stage3-id-enforce ブランチを `feat/rm047-draft-structuring` から作成し、本タスク用の変更をここで管理する
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - Plan:
      - DraftStructuringStep で JobSpec と BriefCard の ID 不一致を検知したら例外を送出し、処理を停止するよう修正します（既存の `logger.debug` でのスキップは廃止）。
      - 上記仕様を保証するテストを追加し、影響範囲の既存テストが通ることを確認します。
      - 仕様が明文化されているドキュメントを確認し、今回の変更点が分かるよう必要なら更新します。
      - テストは `uv run --extra dev pytest` を予定しています。
    - 対象整理（スコープ、対象ファイル、前提）: Stage3 DraftStructuringStep の ID 突合処理と関連ログ出力、BriefNormalization から連携される互換 `content_approved` データを前提にする。
    - ドキュメント／コード修正方針: DraftStructuringStep の ID 確認を例外化し、必要に応じて CLI メッセージとドキュメント（stage-03 requirements など）を更新する。
    - 確認・共有方法（レビュー、ToDo 更新など）: ToDo メモで進捗共有し、PR 説明で影響範囲とテスト結果を報告する。
    - 想定影響ファイル: `src/pptx_generator/pipeline/draft_structuring.py`, `tests/test_draft_structuring_step.py`, `docs/requirements/stages/stage-03-mapping.md` など関連ドキュメント。
    - リスク: 既存データに ID 抜けがある場合にパイプラインが停止するため、エラーメッセージの可読性確保とサンプル更新が必要。
    - テスト方針: 単体テストで ID 不整合時の例外発生を検証し、`uv run --extra dev pytest` で回帰確認する。
    - ロールバック方法: 例外化部分を元のログ出力に戻し、テスト／ドキュメントの追加分を revert する。
    - 承認メッセージ ID／リンク: ユーザー返信「ok, roadmapに新規RM-0XXX番号を採番し、todoファイルを作成して対応を進めよう。」（2025-11-08）
- [ ] 設計・実装方針の確定
  - メモ: 
- [ ] ドキュメント更新（要件・設計）
  - メモ: 要件・設計の合意内容を整理し、迷う点はユーザーへ相談した結果を残す
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [x] 実装
  - メモ: DraftStructuringStep に ID 不整合検知を追加し、CLI テスト群用に JobSpec 生成ヘルパーを導入。影響範囲は draft_structuring, pipeline/__init__, CLI 統合テスト。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest` を実行し 152 件パスを確認（新規ユニットテスト含む）。
- [x] ドキュメント更新
  - メモ: ロードマップへ RM-060 を追加し、stage-03 要件に ID 整合性ゲートを追記。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
-
