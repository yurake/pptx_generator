---
目的: RM-084 CLI/Pipeline リファクタビリティ向上に向けた初期計画と着手準備
関連ブランチ: chore/rm084-cli-refactorability
関連Issue: #343
roadmap_item: RM-084 CLI/Pipeline リファクタビリティ向上
---

- [x] ブランチ作成・初期コミット・push
  - メモ: chore/rm084-cli-refactorability を main から作成済み。リモート未 push（環境制約のためローカル作業継続）。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: RM-084 の初動として CLI `prepare` コマンドと関連補助ロジックを対象に、責務を CLI 層（引数解析・出力整形）とハンドラ層（実処理）へ分割。既存 CLI ユーザーの引数互換性を維持することを前提とする。
    - ドキュメント／コード修正方針: `src/pptx_generator/cli_handlers/prepare.py`（新設）へハンドラ実装を移し、`cli.py` 側は委譲コードに簡素化。関連ノート（`docs/notes/rm084-refactorability-assessment.md`）へ責務分割メモを追記。
    - 確認・共有方法（レビュー、ToDo 更新など）: Plan 承認内容を本 ToDo に記録し、実装後は PR テンプレート・テスト結果で共有。
    - 想定影響ファイル: `src/pptx_generator/cli.py`, `src/pptx_generator/cli_handlers/prepare.py`, `docs/notes/rm084-refactorability-assessment.md`, 関連テストファイル（`tests/cli/test_cli_prepare_stage_flow.py` 等）。
    - リスク: 例外コードや出力メッセージ変更による既存利用者への影響。依存オブジェクト（Prepare orchestrator 等）の取り扱いを誤ると回帰が発生しうる。
    - テスト方針: `uv run --extra dev pytest tests/cli/test_cli_prepare_stage_flow.py` を中心に CLI prepare まわりを再実行し、必要に応じて追加テストを検討。
    - ロールバック方法: 追加モジュールと `cli.py` の差分を revert すれば元の挙動へ戻せる。ドキュメントは同じコミットで巻き戻し可能。
    - 承認メッセージ ID／リンク: ユーザー返信「ok」（2025-11-30）。
- [ ] 設計・実装方針の確定
  - メモ: Plan 承認内容を踏まえた設計・実装方針をここに記載し、ユーザー確認が必要な論点があれば列挙する。
  - [ ] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [ ] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: CLI `prepare` コマンドの本体を新設ハンドラへ委譲し、`cli_handlers/prepare.py` を追加。関連ユーティリティ関数と例外処理も同ファイルへ移設済み。既存出力メッセージと exit code は維持。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/cli/test_cli_prepare_stage_flow.py` を実行し 9 ケース成功。coverage.xml を生成済み。
- [x] ドキュメント更新
  - メモ: `docs/notes/rm084-refactorability-assessment.md` にハンドラ分離メモを追記。その他ドキュメントは今回未更新（理由は各欄へ記載）。
  - メモ: 変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/roadmap 配下
    - メモ: 仕様変更なしのため更新不要。
  - [x] docs/requirements 配下（実装結果との整合再確認）
    - メモ: CLI prepare の責務整理のみで要件変更なし。更新不要。
  - [x] docs/design 配下（実装結果との整合再確認）
    - メモ: CLI コマンドリファレンスは既存記述で整合。更新不要。
  - [x] docs/runbook 配下
    - メモ: 運用手順変更なし。更新不要。
  - [x] README.md / AGENTS.md
    - メモ: Upfront 情報の更新不要。
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
  - メモ: 今回は関連 Issue 未発行のため引き続き `未作成`。
- [ ] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [ ] PR 作成
  - メモ: PR 番号と URL を記録。ワークフローが未動作の場合のみ理由を記載する。todo-auto-complete が自動更新するため手動でチェックしない。

## メモ
-
