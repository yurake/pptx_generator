---
目的: RM-078 stage 表記統一
関連ブランチ: docs/rm078-stage-terminology
関連Issue: #317
roadmap_item: RM-078 stage 表記統一
---

- [x] ブランチ作成・初期コミット・push
  - メモ: docs/rm078-stage-terminology ブランチ作成。初期コミットで ToDo を更新。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: リポジトリ全体で stage 表記を「stage」へ統一。Markdown / reStructuredText / JSON / Python docstring / CLI メッセージを対象にし、誤置換を避けるため日本語文脈での確認を行う。
    - ドキュメント／コード修正方針: `rg` と `python` スクリプトを併用して置換候補を抽出し、手動で適用。Mermaid 図や表記揺れを含む箇所は文脈に合わせて調整し、必要に応じて段落の追記で意味を補う。
    - 確認・共有方法（レビュー、ToDo 更新など）: 主要ドキュメント（README、AGENTS、docs/requirements、docs/design）ごとに変更点を ToDo メモへ追記し、PR で確認観点を列挙する。
    - 想定影響ファイル: `README.md`, `AGENTS.md`, `docs/**`, `src/pptx_generator/cli.py`（メッセージ類）, その他 stage 表記を含むサンプル類。
    - リスク: 固有名詞や履歴で「stage」のままが望ましい箇所を誤って置換するリスク。自動置換による diff 崩壊に注意し、段階的にコミットを分ける。
    - テスト方針: `rg "stage"` で残存確認。必要に応じて `pytest` をサンプリング実行し、文字列置換によるテストログ影響がないか確認する。
    - ロールバック方法: 各ドキュメントの置換コミット単位で revert 実施。重大な誤置換があれば該当ファイルを `git checkout` で戻した上で再編集する。
    - Plan 承認内容:
      1. `rg` で stage 表記候補を抽出し、対象箇所をリスト化する。
      2. 文脈を確認しながら「工程」→「stage」へ置換し、主要ドキュメント・CLI メッセージを更新する。
      3. 置換後に再検索と `uv run --extra dev pytest`（サンプリング）で検証し、副作用を確認する。
      4. 変更概要と確認事項を ToDo メモおよび関連ドキュメントに反映し、必要なら補足ノートを追加する。
    - 承認メッセージ ID／リンク: ユーザー承認「ok」（2025-11-24 の会話メッセージ）を参照。
- [x] 設計・実装方針の確定
  - メモ: 
    - `rg "stage"` で抽出した結果を確認し、以下のカテゴリで表記揺れが発生していることを把握。
      - ルート: `README.md`, `AGENTS.md`
      - ドキュメント: `docs/AGENTS.md`, 各種 `docs/notes/`, `docs/design/`, `docs/requirements/`, `docs/policies/`, `docs/runbooks/`, `docs/qa/`, `docs/roadmap/`、ToDo テンプレ・アーカイブ
      - 設定・サンプル: `config/layout_ai_policies.json`, `samples/**`（text・json・prepare 出力）
      - 実装: `src/pptx_generator/cli.py`, `src/pptx_generator/pipeline/**`, `src/pptx_generator/content_import/**`
      - テスト: `tests/test_cli_integration.py`, `tests/test_mapping_step.py` など CLI／パイプライン関連
    - 大量発生箇所はドキュメント配下が中心。置換は Python スクリプトで自動化し、変換後に主要文書を手動で読み合わせて不自然な表現（例: `stage 別`）を修正する。
    - 数値付き表記（例: `工程3`, `工程 3`）は正規表現で `stage 3` 形式へ統一し、Mermaid 図・表のヘッダーも合わせて変更する。
    - CLI メッセージやテスト期待値も同様に更新し、`stage` 固有名詞の大文字小文字は既存実装に合わせて小文字始まりを基本とする。
- [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - メモ: 置換手順と確認方法は本 ToDo メモへ集約し、追加資料は不要と判断。
- [x] ドキュメント更新（要件・設計）
  - メモ: 確定した設計・実装方針を要件／設計ドキュメントへ反映し、変更不要の場合も必ず理由をメモに記録して `[x]` を付ける
  - [x] docs/requirements 配下
  - [x] docs/design 配下
- [x] 実装
  - メモ: `rg -l 工程` で抽出した 145 ファイルを Python スクリプトで一括変換し、数値付き表記を `stage <番号>` へ正規化。追加スクリプトで和文との間にスペースを挿入し、不自然な箇所（HITL stage など）を手動で調整した。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest` を実行し 217 件成功・1 件スキップを確認（14.12s）。
- [x] ドキュメント更新
  - メモ: README・AGENTS 系・docs/requirements/design/policies/runbooks/notes/qa/roadmap、各 ToDo テンプレ／アーカイブ、config/samples 配下を stage 表記へ統一。主要節はスペース調整後に読み合わせを実施。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [x] チェックリスト整合確認
  - メモ: 各サブチェックが stage 表記統一作業と一致していることをレビューし、未記入項目がないことを確認。
- [x] PR 作成
  - メモ: PR #327 https://github.com/yurake/pptx_generator/pull/327（2025-11-27 完了）

## メモ
