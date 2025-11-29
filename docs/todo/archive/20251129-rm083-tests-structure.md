---
目的: RM-083 テストディレクトリ整備
関連ブランチ: chore/rm083-tests-structure
関連Issue: #334
roadmap_item: RM-083 テストディレクトリ整備
---

- [x] ブランチ作成・初期コミット・push
  - メモ: 2025-11-29 に `main` から `chore/rm083-tests-structure` を作成し、コミット `chore(rm083): bootstrap test restructuring` / `chore(rm083): record branch bootstrap` / `docs: sync agent guidelines` をリモートへ push 済み。
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 承認済み Plan をそのまま転記する。以下の項目を含めること。
    - 対象整理（スコープ、対象ファイル、前提）: `tests/` 直下に残っている単体テストを責務ごとのサブディレクトリへ再配置し、`tests/AGENTS.md` が示す命名・マーカー・フィクスチャ運用に合わせる。既存の `tests/slide_ai/`・`tests/layout_ai/` などの構成を基準に整理する。
    - ドキュメント／コード修正方針: テストファイルは `git mv` / リネームで再配置し、必要に応じて `conftest.py` を分割。ガイドラインは `tests/AGENTS.md` を更新し、ロードマップ／ToDo に進捗を反映する。
    - 確認・共有方法（レビュー、ToDo 更新など）: 各ステップ完了時に本 ToDo を更新し、必要に応じて追加の指示をチャットで確認する。
    - 想定影響ファイル: `tests/**/*.py`, `tests/conftest.py`, `tests/AGENTS.md`, 付随する `docs/roadmap/roadmap.md`, `docs/todo/20251129-rm083-tests-structure.md`
    - リスク: pytest 収集経路の変更でテストが漏れる可能性、`conftest.py` のスコープ変更による副作用、命名変更に伴う import 破損。
    - テスト方針: `uv run --extra dev pytest` をフル実行し、必要に応じてドメインごとのピンポイント実行で切り分ける。
    - ロールバック方法: テスト再配置を行うコミットを `git revert` して元のフラット構成へ戻せるよう、論理単位ごとにコミットを分割する。
    - 承認メッセージ ID／リンク: 2025-11-29 ユーザー発言「ok」
- [x] 設計・実装方針の確定
  - メモ: ドメイン一覧を洗い出し、`tests/<domain>/test_<対象>_<シナリオ>.py` 形式に統一。`git mv` で 50 本のテストを移動・改名し、`sys.path` 参照（`tests/todo/`）とサンプル参照（`tests/cli/`、`tests/layout_validation/`）を階層対応に更新。`slide_ai` ロガーテスト向けにフィクスチャでロガー状態をリセットし、サブディレクトリ導入後の副作用を吸収する。
- [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - メモ: 追加の設計メモは不要（本 ToDo の設計欄で完結）。
- [x] ドキュメント更新（要件・設計）
  - メモ: 確定した設計・実装方針を要件／設計ドキュメントへ反映し、変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/requirements 配下
    - メモ: テストディレクトリ再編は要件定義に影響しないため変更不要。
  - [x] docs/design 配下
    - メモ: 設計ドキュメントの更新は不要（実装責務の再配置のみ）。
- [x] 実装
  - メモ: `git mv` でテストを新ディレクトリへ移動し、`tests/todo/` と `tests/cli/` 等でパス解決を修正。`tests/slide_ai/test_openai_client_error_handling.py` にロガーリセット用フィクスチャを追加。`tests/AGENTS.md` を新構成へ合わせて更新。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest`（231 passed, 1 skipped, 13.09s）
- [x] ドキュメント更新
  - メモ: 結果と影響範囲を整理し、迷う点は必ずユーザーへ相談した結果を残す
  - [x] docs/roadmap 配下
    - メモ: `docs/roadmap/roadmap.md` に RM-083 を追加済み。
  - [x] docs/requirements 配下（実装結果との整合再確認）
    - メモ: 変更なしを確認済み。
  - [x] docs/design 配下（実装結果との整合再確認）
    - メモ: 変更なしを確認済み。
  - [x] docs/runbook 配下
    - メモ: 今回の変更では更新不要。
  - [x] README.md / AGENTS.md
    - メモ: `AGENTS.md` / `tests/AGENTS.md` を新しい参照フローへ更新済み。
- [x] 関連Issue 行の更新
  - メモ: フロントマターの `関連Issue` が `未作成` の場合は、対応する Issue 番号（例: `#123`）へ更新する。進捗をissueに書き込むものではない。
- [x] チェックリスト整合確認
  - メモ: 子タスクをすべて完了した親タスクが未チェックになっていないか確認し、必要に応じて `[x]` へ更新する。親タスクのメモに完了内容を残す。
- [x] PR 作成
  - メモ: PR #335 https://github.com/yurake/pptx_generator/pull/335（2025-11-29 完了）

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
