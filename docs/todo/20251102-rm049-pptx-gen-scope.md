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
    - 追記Plan
      - **スコープ**: `pptx compose` で統合された工程4/5仕様を `feat/rm049-pptx-gen-scope` に反映し、CLI・パイプライン・テスト・ドキュメントを新仕様へ揃える。後方互換対応は不要。
      - **主な作業**
        1. `origin/main` に入った `pptx compose` の差分を確認し、既存実装との競合箇所と影響範囲（CLI／パイプライン／ドキュメント／テスト）を整理する。
        2. CLI とパイプライン実装を `compose` ベースへ更新し、不要なラッパーや旧フローを整理する。
        3. CLI 統合テストおよびパイプライン系テストを `compose` 前提の入出力に合わせて更新し、必要な補助コードを調整する。
        4. README、設計／要件ドキュメント、runbook、サンプルを `compose` 手順に合わせて改訂し、影響と理由を `docs/` 内に記録する。
        5. ToDo と関連ドキュメントに進捗メモと判断事項を整理する。
      - **想定影響ファイル**: `src/pptx_generator/cli.py`、`src/pptx_generator/pipeline/*`、`tests/test_cli_integration.py` ほか CLI 関連テスト、`README.md`、`docs/design/*`、`docs/requirements/*`、`docs/runbooks/*`、`samples/*`。
      - **リスク**: 既存の `generate_ready` ベース実装との矛盾、パイプライン出力・監査ログキーの齟齬、テスト更新漏れ、ドキュメントと実装の不整合。
      - **テスト戦略**: `uv run --extra dev pytest tests/test_cli_integration.py` を中心にパイプライン系単体テストを必要に応じて実行し、可能なら `uv run pptx compose ...` で手動確認する。
      - **ロールバック方法**: 取り込み後のコミットをリバートし、ブランチを `origin/main` の状態へ戻して再検討する。
      - **承認メッセージ ID**: user-msg-rm049-plan-approval
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
- [ ] 工程4・5統合 `pptx compose` 取り込み
  - [x] `origin/main` の `pptx compose` 差分を調査し、CLI／パイプライン／テスト／ドキュメントの影響を整理する。
    - メモ:
      - `compose` コマンドは工程4アウトライン→工程5マッピングを連続実行し、`rendering_ready.json` 生成を前提とした CLI・テスト・ドキュメント全面更新が入っている。
      - `gen` コマンドは JobSpec を受けて工程4/5を通しで実行し直す設計に戻っており、`generate_ready.json` を直接入力する現行フローと乖離している。
      - パイプラインと監査ログのアーティファクトキーは `rendering_ready` 系に統一されているため、`generate_ready` リネーム方針と突き合わせた整合調整が必要。
      - 新しい統合テストは工程4/5の連携を検証しており、出力ディレクトリや生成物パスの命名差異を吸収する必要がある。
  - [x] 取り込み計画に沿った更新内容を具体化し、ToDo の進捗記録を整える。
    - メモ:
      - `compose` 導入に伴い、工程4/5の実行フローを「outline→mapping→gen」の連携に整理し、`generate_ready` 基準で成果物・ログの命名を統一する方針に更新。
      - `pptx gen` は Spec 入力→mapping→render を一括実行する設計へ戻し、工程5は `gen` へ一本化する方針を共有済み。
  - [x] CLI・パイプライン実装を `compose` ベースへ反映し、不要な旧フローを整理する。
    - メモ:
      - `gen` コマンドを Spec 入力に戻し、内部で mapping→render を連携させるよう再実装。`GenerateReadyDocument` を直接扱うことで rename 方針と整合させた。
      - `render` コマンド互換は撤廃し、`compose` で生成した成果物は `gen` 実行時の監査ログに参照として残す運用へ移行。
  - [x] CLI 統合テストおよび関連パイプラインテストを `compose` 前提に更新して実行結果を記録する。
    - メモ: `uv run --extra dev pytest tests/test_cli_integration.py` を実行し 30 件成功。
  - [x] README・設計・要件・runbook・サンプルを `compose` 基準で改訂し、変更内容を `docs/` に記録する。
    - メモ: README と CLI ガイドを `render` / `compose` 前提へ更新し、 `generate_ready` 命名へ統一。
  - [x] 影響範囲と判断事項を整理したメモを `docs/` 配下へ追加し、対応状況を共有する。
    - メモ: `docs/notes/20251108-compose-integration.md` に決定事項と残課題を記録。
  - [x] `pptx render` コマンド廃止と `pptx gen` への統合
    - [x] CLI 実装から `render` サブコマンドを削除し、`gen` へ工程4/5統合フローを集約した。
    - [x] テスト／ドキュメントを `render` 廃止前提へ更新し、一括実行手順を `gen` に統一した。
    - [x] 差分メモを追記し、後方互換不要方針を明記した。
- [ ] PR 作成
  - メモ:

## メモ
**主変更点**
- `src_pptx_generator/models.py`, `src/pptx_generator/generate_ready.py`, `src/pptx_generator/cli.py`: 工程4成果物を `generate_ready.json`／`GenerateReadyDocument` 系へ改称し、`pptx gen` を工程4/5統合コマンドとして再構成。互換用の `pptx render` ラッパーと `_execute_generate_ready_command` を撤廃しました。
- `src/pptx_generator/pipeline/mapping.py`, `src/pptx_generator/pipeline/render_audit.py`: マッピング出力・アーティファクトキーを `generate_ready` 系に統一し、ログ／監査メタも新キーへ更新しました。
- `tests/test_cli_integration.py`, `tests/test_generate_ready_utils.py`, `tests/test_mapping_step.py`, `tests/test_analyzer.py`: CLI テスト群を `generate_ready.json` 前提に書き換え、新しいレンダリング用テストを追加。旧 `rendering_ready` ユーティリティテストは削除し新ファイルへ差し替えました。
- README、`docs/design/cli-command-reference.md`、`docs/requirements/stages/stage-04|05-rendering.md`、runbook／roadmap／AGENTS など関連ドキュメントとサンプル文書をすべて `generate_ready.json`／新しい工程5運用に合わせて更新し、旧「工程3〜5一括」記述を削除。また該当ノート類に現行仕様との差分注記を追加しました。
- `docs/todo/20251102-rm049-pptx-gen-scope.md`: 進捗（実装・テスト・ドキュメント反映）をチェック済みに更新し、方針メモを追加しました。

**テスト**
- `uv run --extra dev pytest tests/test_cli_integration.py`

必要に応じて `uv run pptx gen <generate_ready.json>` で動作確認し、残タスク（PR 作成など）を進めてください。
