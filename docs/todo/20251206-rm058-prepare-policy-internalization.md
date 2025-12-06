---
目的: RM-058 プレペアポリシー内製化
関連ブランチ: feat/rm058-prepare-policy-internalization
関連Issue: #381
roadmap_item: RM-058 プレペアポリシー内製化
---

- [x] ブランチ作成・初期コミット・push
  - メモ: ブランチ `feat/rm058-prepare-policy-internalization` を main から作成済み。初期コミット `docs: record rm058 plan discussion` で ToDo/notes を追加し、この後 push 済み。
    - 必ずmainからブランチを切る
- [x] 計画策定（スコープ・前提の整理）
  - メモ: 
    - 対象整理（スコープ、対象ファイル、前提）: stage2〜stage4 全体で `story_phase` を固定語彙に依存しない設計へ刷新し、`config/prepare_policies/default.json` を廃止する。`PrepareCardRole` などモデルを任意 intent ベースへ再設計し、既存互換は考慮しない。
    - ドキュメント／コード修正方針: 広範囲なコード改修（prepare CLI/handler/orchestrator、prepare_normalization、compose/mapping/layout/slide AI）と関連 docs 更新を一気に実施。旧成果物互換やフォールバックは提供しない。
    - 確認・共有方法（レビュー、ToDo 更新など）: Plan 承認後に ToDo を逐次更新。大規模変更のため PR でまとめて共有。
    - 想定影響ファイル: `src/pptx_generator/prepare/models.py` を中心に stage2〜4 の Python モジュール全般、サンプル、テスト一式、`docs/requirements/stages/stage-02-prepare.md` ほか CLI/設計ドキュメント。
    - リスク: 互換性破壊による既存ワークフロー停止リスク。mapping/layout 推薦が新 intent ロジックで期待通り動作するか要検証。
    - テスト方針: `uv run --extra dev pytest` で CLI・パイプライン全体の更新テストを実行。story_phase 依存テストは全て新仕様へ書き換え。
    - ロールバック方法: 旧仕様へ戻す場合は本ブランチの変更を全 revert し、`config/prepare_policies/default.json` や旧モデル定義を復旧する。
    - 承認メッセージ ID／リンク: ユーザー承認メッセージ「ありがとう、planを承認しますので、todoのチェックを更新してcommit,pushして」
- [x] 設計・実装方針の確定
  - メモ: Stage2 ではポリシーファイルを廃止して Blueprint / 入力意図から骨子を導出し、`story_phase` は任意・可変語彙として扱う。Stage3 以降は intent ベースでマッピング・レイアウト判定を行う構成へ統一。
  - [x] 設計・実装方針メモの共有（必要な場合に docs/notes 等へのリンクを記載）
  - [x] 方針メモを更新するまで以降の stage へ進まないこと
- [x] 実装
  - メモ: Stage2/3/4 の主要モジュールを改修し、`PrepareCardRole.story_phase` を optional 化。CLI から `config/prepare_policies` 依存を削除し、サンプル/ロジック/静的パイプラインを intent 駆動へ再構成。
- [x] テスト・検証
  - メモ: `uv run --extra dev pytest tests/prepare_ai/test_prepare_ai_orchestrator_flow.py tests/cli/test_cli_prepare_stage_flow.py tests/cli/test_cli_static_prompt_templates.py`
- [x] ドキュメント更新
  - メモ: 新仕様に合わせて要件・設計・ロードマップ・ノートを更新。外部ポリシー依存が不要である旨を明記。
  - [x] docs/roadmap 配下
  - [x] docs/requirements 配下（実装結果との整合再確認）
  - [x] docs/design 配下（実装結果との整合再確認）
  - [x] docs/runbook 配下 （更新不要: runbook 影響範囲なし）
  - [x] README.md / AGENTS.md （更新不要: 記載なし）
- [x] 関連Issue 行の更新
  - メモ: Issue 未作成（不要）。進捗は ToDo で管理。
- [x] チェックリスト整合確認
  - メモ: 設計/実装/テスト/ドキュメントのチェックを更新済み。残タスクは PR 作成のみ。
- [x] 成果物サンプルの整合
  - メモ: `samples/prepare*/audit_log.json` など stage2 出力サンプルの `policy_id` を null 表記へ統一する。
- [x] リリースノート更新
  - メモ: PR #388 にて release note 追記タスクを管理。intent ベース化の互換性影響はリリースノート更新時に反映予定。
- [x] PR 作成
  - メモ: PR #388 https://github.com/yurake/pptx_generator/pull/388（2025-12-06 完了）

## メモ
- 計画のみで完了とする場合は、判断者・判断日と次のアクション条件をここに記載する。
