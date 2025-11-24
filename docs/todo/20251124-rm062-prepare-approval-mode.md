---
目的: RM-062 pptx prepare 承認モード整備
関連ブランチ: feat/rm062-prepare-approval-mode
関連Issue: 未作成
roadmap_item: RM-062 pptx prepare 承認モード整備
---

- [ ] ブランチ作成・初期コミット・push
  - メモ: 2025-11-24 main から feat/rm062-prepare-approval-mode を作成。`docs(rm062): add todo for prepare approval mode` を初期コミットとして作成済み。push は Plan 承認後に実施予定。
- [ ] 計画策定（スコープ・前提の整理）
  - メモ: 2025-11-24 ユーザー承認済み Plan を転記。
    - 対象整理（スコープ、対象ファイル、前提）:
      - CLI `pptx prepare` の承認モード／旧 `--approved` 系オプション残存有無を確認し、必要であれば実装を整理する。
      - 利用者向けドキュメント（`README.md`, `docs/design/cli-command-reference.md`, `docs/runbooks/story-outline-ops.md` など）から CLI で承認状態を扱う旨の記述を排除し、PrepareStore/prepare_log へ誘導する。
      - 現状仕様がドキュメントと乖離していないかを棚卸し、補足が必要な設計メモ（例: `docs/design/schema/stage-02-content-normalization.md`）を確認する。
    - ドキュメント／コード修正方針:
      - CLI `--help` 表記と実装コメントを最新仕様（承認は Store 側）にそろえる。
      - ドキュメントの CLI 解説／運用手順から承認モードに関する記述を更新し、必要なら PrepareStore 連携フローを追記する。
      - 追加で触れたファイルは ToDo に記載し、他ドキュメントとの整合を確認する。
    - 確認・共有方法（レビュー、ToDo 更新など）:
      - ステークホルダー確認は本 ToDo を更新し、Plan 承認メッセージ ID を PR・ToDo 双方へ記載する。
      - ドキュメント修正は差分確認しやすいように分割コミットを検討する。
    - 想定影響ファイル:
      - `src/pptx_generator/cli.py`
      - `README.md`
      - `docs/design/cli-command-reference.md`
      - `docs/runbooks/story-outline-ops.md`
      - `docs/design/schema/stage-02-content-normalization.md`（必要に応じて）
      - その他 CLI 周辺ドキュメント
    - リスク:
      - 旧 CLI オプションを削除する場合、既存スクリプトとの互換性低下。
      - ドキュメント更新のみで実装と整合しない状態が残る可能性。
    - テスト方針:
      - コード修正が発生した場合は `uv run --extra dev pytest tests/test_cli_prepare.py tests/test_cli_integration.py -k prepare` を実行。
      - ドキュメント更新のみの場合はビルド等不要であることを確認。
    - ロールバック方法:
      - コード変更時は該当コミットを巻き戻して旧 CLI 挙動・ドキュメントを復元する。
      - ドキュメントのみの場合は差分を戻すことで対応。
    - 承認メッセージ ID／リンク: （このスレッドの OK メッセージを記録）
- [ ] 設計・実装方針の確定
  - メモ: 未着手。
- [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - メモ: 未着手。
- [ ] ドキュメント更新（要件・設計）
  - メモ: 未着手。
  - [ ] docs/requirements 配下
  - [ ] docs/design 配下
- [ ] 実装
  - メモ: 未着手。
- [ ] テスト・検証
  - メモ: 未着手。
- [ ] ドキュメント更新
  - メモ: 未着手。
  - [ ] docs/roadmap 配下
  - [ ] docs/requirements 配下（実装結果との整合再確認）
  - [ ] docs/design 配下（実装結果との整合再確認）
  - [ ] docs/runbook 配下
  - [ ] README.md / AGENTS.md
- [ ] 関連Issue 行の更新
  - メモ: 未着手。
- [ ] チェックリスト整合確認
  - メモ: 未着手。
- [ ] PR 作成
  - メモ: 未着手。

## メモ
- 
