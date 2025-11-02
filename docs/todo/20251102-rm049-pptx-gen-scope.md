---
目的: `pptx gen` の工程5専用コマンド化と責務整理に向けた現状調査と施策検討
関連ブランチ: feat/rm049-pptx-gen-scope
関連Issue: #258
roadmap_item: RM-049 pptx gen スコープ最適化
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/rm049-pptx-gen-scope を main から作成し、本 ToDo を初期コミットとして追加。
- [x] 計画策定（スコープ・前提の整理）
  - メモ:
    - スコープ
      - 工程4成果物のファイル名と関連アーティファクトを `rendering_ready.json` から `generate_ready.json` へ改称し、CLI／パイプライン全体で参照を更新する。
      - `pptx gen` を工程5専用コマンドとして再構成し、Spec 入力および工程3/4向けオプション（`--content-approved` など）を削除して `generate_ready.json` を必須入力とする。
      - テスト・サンプル・ドキュメントを新名称と新 CLI 手順に合わせて更新し、旧「工程3〜5一括」記述や `uv run pptx render` の利用例を整理する。
    - 想定影響ファイル
      - `src/pptx_generator/cli.py`、`src/pptx_generator/pipeline/` 配下の関連モジュール。
      - `tests/test_cli_integration.py` ほか `generate_ready` を前提としたテストケース。
      - `README.md`、`docs/design/cli-command-reference.md`、`docs/requirements/stages/stage-05-rendering.md`、`docs/runbooks/support.md`、関連ノート類。
    - リスク
      - ファイル名変更に伴う参照漏れ（コード・テスト・ドキュメント・監査ログ）が発生する可能性。
      - `audit_log.json` やモニタリングメタのキー名変更による整合性崩れ。
    - テスト方針
      - `uv run --extra dev pytest tests/test_cli_integration.py` を実行し、新しい `generate_ready.json` 前提の CLI フローを確認する。
      - 必要に応じて `tests/test_renderer.py` 等の関連単体テストで回帰チェックを行う。
    - ロールバック方法
      - CLI／パイプライン／ドキュメントの変更を差し戻し、成果物名を `generate_ready.json` に復旧する。
    - 承認メッセージ ID／リンク: user-msg-rm049-plan-approval
- [x] 設計・実装方針の確定
  - メモ: `generate_ready.json` への統一と `pptx gen`（工程5専用）を中心とした CLI 体系で進める。
- [x] ドキュメント更新（要件・設計）
  - メモ: stage-04/05 要件と CLI リファレンスを `generate_ready.json` と新 `pptx gen` に合わせて更新。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ:
    - [x] コード・テスト・ドキュメントの `rendering_ready` 参照を洗い出し、`generate_ready` へ名称変更する。
    - [x] `pptx gen` を工程5専用フローに再構成し、Spec 入力や工程3/4向けオプションを削除する。
    - [x] CLI 統合テストなどを `generate_ready.json` 前提に更新し、`uv run --extra dev pytest tests/test_cli_integration.py` を実行する。
    - [x] README / 設計 / 要件 / runbook から旧「工程3〜5一括」記述を削除し、新手順へ更新する。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/test_cli_integration.py` を実施。
- [x] ドキュメント更新
  - メモ: README / roadmap / runbook / AGENTS を新仕様に合わせて追従。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ:
- [ ] PR 作成
  - メモ:

## メモ
**主変更点**
- `src_pptx_generator/models.py`, `src/pptx_generator/generate_ready.py`, `src/pptx_generator/cli.py`: 工程4成果物を `generate_ready.json`／`GenerateReadyDocument` 系へ改称し、`pptx gen` を工程5専用コマンドとして再構成。内部ヘルパー `_execute_generate_ready_command` を追加し、`pptx render` は互換ラッパーとして同ヘルパーを呼び出すよう整理しました。
- `src/pptx_generator/pipeline/mapping.py`, `src/pptx_generator/pipeline/render_audit.py`: マッピング出力・アーティファクトキーを `generate_ready` 系に統一し、ログ／監査メタも新キーへ更新しました。
- `tests/test_cli_integration.py`, `tests/test_generate_ready_utils.py`, `tests/test_mapping_step.py`, `tests/test_analyzer.py`: CLI テスト群を `generate_ready.json` 前提に書き換え、新しいレンダリング用テストを追加。旧 `rendering_ready` ユーティリティテストは削除し新ファイルへ差し替えました。
- README、`docs/design/cli-command-reference.md`、`docs/requirements/stages/stage-04|05-rendering.md`、runbook／roadmap／AGENTS など関連ドキュメントとサンプル文書をすべて `generate_ready.json`／新しい工程5運用に合わせて更新し、旧「工程3〜5一括」記述を削除。また該当ノート類に現行仕様との差分注記を追加しました。
- `docs/todo/20251102-rm049-pptx-gen-scope.md`: 進捗（実装・テスト・ドキュメント反映）をチェック済みに更新し、方針メモを追加しました。

**テスト**
- `uv run --extra dev pytest tests/test_cli_integration.py`

必要に応じて `uv run pptx gen <generate_ready.json>` で動作確認し、残タスク（PR 作成など）を進めてください。
