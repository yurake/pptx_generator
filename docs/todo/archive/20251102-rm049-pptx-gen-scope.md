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
      - 工程4成果物のファイル名と関連アーティファクトを `generate_ready.json` から `generate_ready.json` へ改称し、CLI／パイプライン全体で参照を更新する。
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
    - 計画更新（2025-11-10）
      - **スコープ**: `pptx gen` を `generate_ready.json` 入力＋ブランド設定に統一し、工程4成果物のテンプレ参照と監査メタを揃えた上で CLI・テスト・ドキュメントを整理する。
      - **テスト戦略**: `uv run --extra dev pytest` を基本とし、必要に応じて CLI フロー（compose→mapping→gen）と PDF 変換を手動確認する。
      - **ロールバック方法**: 当該変更コミットを revert し、`generate_ready.json` 前提統合前の CLI 実装へ戻す。
      - **実施ステップ**
        1. ToDo と差分内容を突き合わせ、現状の CLI／パイプライン／テスト差分を整理する。
        2. CLI とパイプラインを `generate_ready` 専用仕様へ整備し、テンプレ参照や監査メタが欠落しないよう調整する。`render` コマンドの扱いも同時に判断する。
        3. CLI 系テストを新仕様へ更新し、`uv run --extra dev pytest` で緑化する。
        4. README・設計・要件・runbook・サンプル・ToDo を刷新し、Plan 承認 ID を含む記録を更新する。
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
    - 追加Plan（generate_ready 専用 CLI 化）
      - **スコープ**: `pptx gen` を generate_ready + branding 入力へ統一し、工程4出力にテンプレ参照を含めた上で CLI・テスト・ドキュメントを刷新する。
      - **主な作業**
        1. MappingStep で `generate_ready` メタへテンプレートパスを埋め込み、工程5が追加引数なしでテンプレートを特定できるようにする。
        2. CLI `pptx gen` を generate_ready 専用の引数体系へ変更し、`--template` / `--content-approved` を廃止する。
        3. mapping で出力した成果物（`mapping_log` など）を工程5に引き継ぐアーティファクト整備を行う。
        4. CLI 統合テストやチートシートテストを新しい入力仕様へ書き換え、成功ケース／エラーケースを再検証する。
        5. README・CLI ガイド・ノート類を更新し、新しい CLI 仕様と注意点（テンプレートパス埋め込みへの依存）を明文化する。
      - **テスト戦略**: `uv run --extra dev pytest tests/test_cli_integration.py` に加え、`tests/test_cli_cheatsheet_flow.py` を generate_ready ルートで成功させる。
      - **ロールバック方法**: 変更コミットを差し戻し、従来の Spec 入力＋`--template`／`--content-approved` 前提の CLI に戻す。
      - **承認メッセージ ID**: _pending approval_
    - 追加Plan（generate_ready 詳細設計）
      - **スコープ**: `generate_ready.json` のメタ情報（テンプレ参照・将来拡張用フィールド）を整理し、CLI 変更に先立って設計を固める。
      - **主な作業**
        1. `generate_ready` に含めるテンプレ参照（パス形式やバージョン識別子の要否）を決定し、仕様を文書化する。
        2. 監査ログおよびマッピングメタへの反映方針を整理し、必要な更新箇所を列挙する。
        3. 設計内容を docs/notes に記録し、本 ToDo から参照できるようリンクを追加する。
      - **テスト戦略**: 設計タスクのため該当なし（実装フェーズで統合テストを実施）。
      - **ロールバック方法**: 設計メモの破棄または更新停止で対応。
      - **承認メッセージ ID**: _pending approval_
    - 追加Plan（template サブコマンド維持）
      - **スコープ**: `pptx template` サブコマンドを `feat/rm049-pptx-gen-scope` の CLI 構成へ再統合し、テンプレ工程の一括実行（抽出・検証・リリース）を継続提供する。generate_ready 統合後の共通処理と競合しないよう調整し、ドキュメントとテストも復元する。
      - **主な作業**
        1. main ブランチから `template` 関連の実装（`src/pptx_generator/cli.py` の共通ヘルパー、`_run_template_extraction`／`_run_template_release` など）を取り込み、`feat/rm049-pptx-gen-scope` で削除された差分を整理する。
        2. generate_ready 専用化で導入したテンプレ参照メタやアーティファクト管理と整合するよう CLI 実装を調整し、`tpl-extract` / `layout-validate` / `tpl-release` と重複する処理を共通化する。
        3. `tests/test_cli_integration.py` ほかテンプレ工程に関する統合テストを復元・更新し、テンプレ抽出・リリースの期待値が現行成果物に一致することを検証する。
        4. README・`docs/design/cli-command-reference.md` などテンプレ工程を案内する資料を再確認し、`template` サブコマンドを前提とした説明へ整合させる。
      - **テスト戦略**: `uv run --extra dev pytest tests/test_cli_integration.py::test_cli_template_basic` を中心にテンプレ工程の統合テストを実行し、余力があれば CLI 全体テストを追加実行する。
      - **ロールバック方法**: `template` 復元に関するコミットを revert し、テンプレ工程を個別サブコマンド前提へ戻す。
      - **承認メッセージ ID**: _pending approval_
- [x] 設計・実装方針の確定
  - メモ: `generate_ready.json` への統一と `pptx gen`（工程5専用）を中心とした CLI 体系で進める。
- [x] ドキュメント更新（要件・設計）
  - メモ: stage-04/05 要件と CLI リファレンスを `generate_ready.json` と新 `pptx gen` に合わせて更新。
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ:
    - [x] コード・テスト・ドキュメントの `generate_ready` 参照を洗い出し、`generate_ready` へ名称変更する。
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
      - `compose` コマンドは工程4アウトライン→工程5マッピングを連続実行し、`generate_ready.json` 生成を前提とした CLI・テスト・ドキュメント全面更新が入っている。
      - `gen` コマンドは JobSpec を受けて工程4/5を通しで実行し直す設計に戻っており、`generate_ready.json` を直接入力する現行フローと乖離している。
      - パイプラインと監査ログのアーティファクトキーは `generate_ready` 系に統一されているため、`generate_ready` リネーム方針と突き合わせた整合調整が必要。
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
- [x] generate_ready 詳細設計
  - [x] `generate_ready` に埋め込むテンプレ参照／メタ情報の候補（例: `template_path`, バージョン識別子）を整理する。
  - [x] 監査ログや `mapping_meta` への反映方針をまとめ、影響箇所を列挙する。
  - [x] 設計内容を docs/notes に記録し、本 ToDo から参照できるリンクを残す。
    - メモ: `docs/notes/20251109-generate-ready-meta.md` に設計メモを追加。承認メッセージ ID: user-msg-20251109-plan-ok。
- [x] `pptx gen` generate_ready 専用化（ブランド指定のみを必須とする）
  - [x] 工程4出力 (`generate_ready.json`) にテンプレートパスを含めるよう MappingStep を更新する。
  - [x] CLI `pptx gen` を `generate_ready.json` ＋ `--branding` 入力へ一本化し、`--template` / `--content-approved` 等を廃止する。
  - [x] マッピング成果物引き継ぎ（`mapping_log` など）を工程5へ渡すアーティファクト整備を行う。
  - [x] テスト（統合・チートシートなど）を新入力仕様へ書き換えて成功することを確認する。
  - [x] README / ドキュメント / ノートを更新し、新しい CLI 要件と注意事項を明文化する。
    - メモ: `src/pptx_generator/pipeline/mapping.py` と `src/pptx_generator/cli.py` で `template_path`／`mapping_meta` を連携し、`tests/test_cli_integration.py` で generate_ready 専用フローを検証済み。README ほかドキュメントも generate_ready 前提へ更新完了。
- [x] PR 作成
  - メモ: PR #266 https://github.com/yurake/pptx_generator/pull/266（2025-11-03 完了）


- [x] 工程2/3改修の取り込み
- メモ: origin/main の commit 9a34ddb（工程2/3統合・brief導入）を取り込む。
    - [x] 最新 main の差分を精査し、CLI/パイプライン/テスト/サンプル/ドキュメントの影響を整理する。
    - [x] `git merge origin/main` を実行し、`src/pptx_generator/cli.py`、`src/pptx_generator/brief/*`、`pipeline/brief_normalization.py`、`tests/test_cli_*`、`README.md` などで発生する競合を解消する。
      - メモ: PR #266 コンフリクトの主因だった `rendering_ready` への名称変更差分を再度 `generate_ready` に統合し、`compose` 追加部分と整合するよう調整。
    - [x] 工程5専用化で導入した generate_ready フローと、新工程3（brief成果物）が整合するよう CLI・パイプラインを調整する。
    - [x] README・設計／要件／runbook を最新仕様へ更新し、必要に応じて `docs/notes` に決定メモを追加する。
    - [x] `uv run --extra dev pytest`（最低でも CLI/brief 関連テスト）を実行し、`uv run pptx gen .pptx/gen/generate_ready.json --branding config/branding.json --export-pdf` を再確認する。
    - [x] ToDo に結果メモを追記し、必要なら関連 Issue / ロードマップの更新を検討する。
## メモ
**主変更点**
- `src/pptx_generator/cli.py`: `pptx gen` を `generate_ready.json` 専用入力へ統一し、テンプレートパス欠落時にエラーを返す。`pptx mapping` は `--template` 指定を必須化し、監査メタ `mapping_meta` に `template_path` を確実に記録。
- `src/pptx_generator/pipeline/mapping.py`、`src/pptx_generator/generate_ready.py`: `GenerateReadyDocument.meta.template_path` を埋め込み、`mapping_meta` と監査ログにテンプレート情報を反映。
- `tests/test_cli_integration.py` / `tests/test_cli_cheatsheet_flow.py` / `tests/test_mapping_step.py`: generate_ready 専用フローに合わせてテンプレート必須化と新エラーハンドリングを検証。
- README・`docs/design/cli-command-reference.md`・`docs/runbooks/story-outline-ops.md` ほか関連ドキュメントを更新し、`pptx gen` の入力仕様と `--template` 必須化を明記。
- `docs/notes/20251109-generate-ready-meta.md`: Brief 正規化後も generate_ready メタ方針を維持する旨を追記。
- **テスト**
  - `uv run --extra dev pytest`（143 件成功、2025-11-10 実行）
  - メモ: PR #266 コンフリクト解消後に `uv run --extra dev pytest tests/test_cli_integration.py` を再実行し、generate_ready 前提の CLI フローが緑化することを確認（2025-11-XX）。
  - 追記: origin/main からの再マージ後も同テストを実行し、コンフリクト解消版が成功することを確認（2025-11-XX）。

必要に応じて `uv run pptx gen .pptx/gen/generate_ready.json --branding config/branding.json` を再実行し、ブランド切り替えや PDF オプションの挙動を確認してください。
