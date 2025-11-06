---
目的: RM-047 再設計ドキュメント再配置と generate_ready 設計方針の最新化
関連ブランチ: feat/rm047-draft-structuring
関連Issue: #264
roadmap_item: RM-047 テンプレ統合構成生成AI連携
---

- [x] ブランチ作成と初期コミット
  - メモ: feat/rm047-draft-structuring を main から作成済み（既存ブランチを流用済み）。以降の作業は同ブランチ上で実施。
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
      - **対象整理**  
        - スコープ: RM-047 の再設計ドキュメントを `docs/design/stages/` へ統合し、Stage2〜4 の新フローで `generate_ready` を唯一の出力とする前提を整理する。実装コードの改変は行わない。  
        - 対象: `docs/design/stages/stage-04-draft-structuring.md`、`docs/requirements/stages/stage-04-draft-structuring.md`、`docs/design/design.md`、`docs/requirements/requirements.md`、`docs/todo/20251104-rm047-design-refresh.md`。  
        - 前提: main の最新状態ではテンプレ工程が統合され、工程2成果物は `prepare_card.json` へ名称統一され、CLI `pptx outline` が新構成へ再設計済み。  
      - **実施手順**  
        1. 現行 Stage2〜4 関連ドキュメントとテスト解説を精査し、削除済み `docs/design/draft-structuring-RM047.md` 由来で補うべき情報を棚卸しする。  
        2. Stage2→Stage3→Stage4 の新構成を前提に、`generate_ready` 置換方針（CLI／モデル／パイプライン視点）を整理し、再配置ドキュメントの構成案をまとめる。  
        3. 更新が必要なドキュメント・テスト範囲を決定し、今後の編集手順と ToDo チェック項目を整備する。  
      - **想定影響ファイル**: `docs/design/stages/stage-04-draft-structuring.md`、`docs/requirements/stages/stage-04-draft-structuring.md`、`docs/design/design.md`、`docs/requirements/requirements.md`、関連テストドキュメント。  
      - **リスク**: main 側の新仕様との齟齬、旧仕様の記述残存、テスト方針の抜け漏れ。  
      - **テスト方針**: 本フェーズではテスト実行なし。設計反映後の実装タイミングで `uv run --extra dev pytest` などを実施予定。  
      - **ロールバック**: 追加・更新したドキュメントを個別に `git checkout -- <file>`、または該当コミットを `git revert` することで復旧可能。  
      - **承認メッセージ**: ユーザー発言「ok」。
- [x] 設計・実装方針の確定
  - メモ: Stage3（マッピング）で `generate_ready` 系成果物を確定させ、旧工程4（ドラフト構成）はレガシー扱いとする方針を文書化。`docs/design/stages/stage-03-mapping.md` を刷新し、`docs/design/stages/stage-04-draft-structuring.md` へレガシーノートを追記済み。
- [x] ドキュメント更新（要件・設計）
  - メモ: 対象ドキュメントの整合を `generate_ready` 基盤へ更新済み（commit `edfabde`）。
  - [x] docs/requirements 配下
    - 対象: `docs/requirements/stages/stage-03-mapping.md`, `docs/requirements/stages/stage-04-draft-structuring.md`, `docs/requirements/requirements.md` を更新し、`generate_ready` 前提とレガシーノートを反映。
  - [x] docs/design 配下
    - 対象: `docs/design/stages/stage-03-mapping.md`, `docs/design/stages/stage-04-draft-structuring.md`, `docs/design/design.md`, `docs/design/cli-command-reference.md`, `docs/design/20251019-stage3-4-cli.md` を更新し、工程3の成果物・CLI オプション・legacy 注意書きを整理。
- [x] 実装
  - メモ: ドキュメント再配置・レガシー注記追加などの反映を完了（commit `edfabde` ほか）。
- [x] テスト・検証
  - メモ: 実装不要タスクのためテスト対象なし。ドキュメント確認のみ。
- [x] ドキュメント更新
  - メモ: 全関連ドキュメントの整合を確認し、必要箇所は更新済み。
  - [x] docs/roadmap 配下
    - `docs/roadmap/roadmap.md` の工程3説明と RM-024 期待成果を `generate_ready` 基盤へ更新済み（2025-11-04）。他セクションの legacy 記述は今後のロードマップ整理時に再検討。
  - [x] docs/requirements 配下（実装結果との整合再確認）
    - Stage4 記述が `generate_ready` と矛盾しないか最終確認済み。
  - [x] docs/design 配下（実装結果との整合再確認）
    - 設計ドキュメントのフロー図・成果物一覧・CLI セクションが `generate_ready` 基盤を反映していることを確認済み。
  - [x] docs/runbook 配下
  - [x] README.md / AGENTS.md
- [x] 関連Issue 行の更新
  - メモ: 
- [x] PR 作成
  - メモ: PR #273 https://github.com/yurake/pptx_generator/pull/273（2025-11-06 完了）

## メモ
- 現行ステージドキュメント確認結果（更新反映済み）
  - `docs/design/stages/stage-04-draft-structuring.md`: レガシーノートを追加し、旧 `draft_*` フローである旨を明記。
  - `docs/requirements/stages/stage-04-draft-structuring.md`: 同様にレガシーノートを追加。
  - `docs/design/design.md`: 工程3の成果物・入出力表を `generate_ready` 基盤へ更新。
  - `docs/design/stages/stage-03-mapping.md`: 目的・入出力・ワークフローを刷新し、`generate_ready.json` / `generate_ready_meta.json` を中心とした記述へ更新。
- Stage4 再設計案（草案）
  - 成果物: `generate_ready.json` を章/カード割当の主ファイル、`generate_ready_meta.json` を章テンプレ・AI 推薦・Analyzer サマリ・承認タイムラインのメタとして位置付ける。`draft_review_log.json`／`draft_mapping_log.json` は名称維持しつつ `generate_ready` と ID 連携。  
  - フロー: `pptx outline` は `generate_ready` を直接操作し、承認状態を `generate_ready_meta.sections[*].status` で管理。Chapter Template Registry は `generate_ready_meta.template` で適合率を出力し、Analyzer 情報は `sections[*].analyzer_summary` へ集約。  
  - CLI: `pptx outline` は `--draft-*` を廃止し `--generate-ready-filename` 等へ置換。`pptx compose` は Stage3 全体の再実行時に Stage4 モジュールを呼び出し、`pptx mapping` は `generate_ready.json` を唯一の入力とする。  
  - モデル/パイプライン: `GenerateReadyDocument` に HITL 状態を追加し、`generate_ready.py` で Stage4→Stage5 変換を拡張。`pipeline/draft_structuring.py` は `GenerateReadyDocument` を出力し、`pipeline/mapping.py` は旧 `draft_*` 参照を削除。  
  - リスク: CLI オプション変更に伴う互換性問題、`generate_ready_meta.json` 構造確定、既存テスト／ドキュメントの大規模更新が必要。
- ステージ構成の前提
  - 工程は 4 段（1: テンプレ、2: コンテンツ準備、3: マッピング、4: PPTX 作成）。ドキュメント改訂時もこの段構成を維持する。
- 追加で確認が必要なドキュメント／テスト
  - `README.md`: 工程説明と CLI サンプルを最新版へ同期するタスクが残る。
  - `tests/test_cli_integration.py`, `tests/test_cli_outline.py`, `tests/test_generate_ready_utils.py`: ドキュメント更新に合わせた補足コメント・参照リンクの追加を検討。
