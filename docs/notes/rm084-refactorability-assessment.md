# RM-084 リファクタリング優先候補調査メモ（2025-02-16）

## 背景
- CLI とパイプライン各 Stage の主要モジュールに大規模で複雑な関数が散見され、可読性・保守性の悪化を招いている。
- リファクタリング候補を洗い出し、ロードマップに新規テーマとして追加するための調査結果をまとめる。

## 調査対象と所見
- `src/pptx_generator/cli.py`
  - 全体で約 3,600 行に達し、サブコマンドごとのエントリポイントからファイル入出力、パイプライン実行、成果物書き出しまでが 1 つに集中している。
  - `prepare` コマンド実装（`src/pptx_generator/cli.py:2029`）が 190 行超にわたり、例外処理・テンプレ探索・AI オーケストレーション・成果物集約が混在している。
  - CLI 側を引数解析と orchestration 呼び出しに限定し、stage ごとのハンドラへ委譲する構造化が必要。
- `src/pptx_generator/pipeline/mapping.py`
  - `MappingStep.run`（281 行）がカード並び替え、レイアウトスコアリング、テーブルアンカー解決、容量制御、成果物生成を一括で扱っている。
  - 状態を示すローカル変数が多く、副作用が散在しているためステップ別ヘルパーとデータクラス化で責務を分離したい。
- `src/pptx_generator/pipeline/draft_structuring.py`
  - `_build_document`（226 行）がセクション構築、AI 推薦の集計、ログ生成をクロージャ内でまとめて処理している。
  - DraftSection 生成、AI 統計集計、レコメンドログ整備を別コンポーネントへ切り出すことで保守性向上が見込める。
- `src/pptx_generator/prepare_ai/orchestrator.py`
  - `_build_cards_static`（223 行）が Blueprint 展開、章割り当て、LLM プロンプト生成、応答検証、カード変換までを単一メソッドで行う。
  - スロット割り当てやプロンプト構築、LLM 応答検証を個別関数・クラスへ分割し、副作用を減らす余地が大きい。
- `src/pptx_generator/layout_validation/suite.py`
  - `_build_layout_records`（265 行）がアンカー走査、ヒューリスティック評価、AI 呼び出し、警告集約を複雑な辞書操作で処理している。
  - プレースホルダー解析・usage tag 判定・警告生成を専用ビルダーに分離し、データモデル化することで読みやすさを改善できる。
- `src/pptx_generator/api/app.py`
  - `create_app`（280 行超）が FastAPI ルート定義を 1 関数内に保持し、依存取得とエラーハンドリングが重複している。
  - 機能別ルーター分割や共通レスポンス生成ユーティリティ化による分離が望ましい。

## 次のアクション（案）
1. CLI とパイプライン各 Stage の責務分割案を設計し、orchestrator インターフェイスを整理する。
2. Mapping / Draft Structuring / Prepare AI 周辺の長大メソッドを段階的に分割し、テスト観点を整備する。
3. FastAPI ルートを cards・logs など機能単位の router へ切り出し、共通処理をユーティリティ化する。

## 2025-11-30 CLI prepare ハンドラ分離方針メモ
- 対象: `src/pptx_generator/cli.py` 内 `prepare` コマンド（約 320 行）。
- 現状責務:
  - Click オプション検証（入力ファイル、モード、jobspec、page-limit）。
  - Blueprint / jobspec / template_spec 解決とハッシュ計算。
  - プロンプトテンプレート・スライド入力マニフェストの読込。
  - Orchestrator 呼び出し、成果物書き出し、監査ログ生成、標準出力メッセージ表示、エラーコード決定。
- 分割方針:
  - CLI 層: 引数解析、例外 → exit code 変換、ユーザー向けメッセージの一元化。
  - ハンドラ層: ドメイン入力構築（blueprint, prompts, slide inputs）と `PrepareAIOrchestrator` 呼び出し、成果物保存。戻り値で生成パス・メタ情報をまとめ、CLI が echo。
  - 例外: ハンドラで専用例外（例: `PrepareCommandError`）を送出し、エラー分類（入力/IO/AI/設定）を enum で保持→ CLI 側の exit code 互換性を担保。
- 実装メモ:
  - `src/pptx_generator/cli_handlers/prepare.py` を新設。`PrepareCommandConfig`（入力値 struct）、`PrepareCommandResult`（成果物パスと監査メタ）を定義。
  - ハンドラ内でファイル生成を集約、`_dump_json` 等のユーティリティを再利用できるよう CLI 側ヘルパーを共有化（必要なら `utils/io.py` へ移動検討）。
  - CLI からは `invoke_prepare_command(config)` を呼び出し、結果を標準出力に整形。
  - 静的モード制約（page-limit 禁止など）はハンドラに集約し、CLI では `mode` 変換後に config 生成のみ行う。
  - 既存テスト `tests/cli/test_cli_prepare_stage_flow.py` が通るよう出力パスとメッセージを変えない。新設ハンドラの単体テストで `PrepareCommandConfig` → ファイル生成を検証予定。

## 2025-11-30 MappingStep.run リファクタ設計メモ
- 対象: `src/pptx_generator/pipeline/mapping.py` の `MappingStep.run`（約 280 行）。
- 現状フローと責務:
  1. **入力読み込み**: draft/context アーティファクト確保、レイアウトカタログ読込。
  2. **ワークアイテム構築**: セクション順カードを並べ替え、spec との付き合わせを行う。
  3. **スライド処理ループ**: 候補スコア計算 → card ヒューリスティック適用 → レイアウト選択 → テーブルアンカー解決 → 容量制御 → GenerateReady/ログの生成。
  4. **成果物書き出し**: `generate_ready.json`、`mapping_log.json`、fallback レポートの保存とアーティファクト登録。
  5. **統計集計**: フォールバック件数、AI パッチ件数、テンプレートメタなどを `mapping_meta` へ記録。
- 分割方針:
  - `MappingAccumulator` で出力リスト／統計情報／コンテキスト共通値を保持し、副作用を局所化。
  - `_build_work_items(context, draft_document, content_lookup)` でループ入力を前処理。
  - `_process_work_item(item, accumulator, previous_layout)` で単一スライド処理（候補スコア→レイアウト選定→要素組み立て→容量制御→ログ構築）を実施。
  - `_finalize_outputs(...)` で JSON 書き出しとアーティファクト登録を一括実行。
  - 既存 helper（`_score_candidates`, `_build_elements`, `_apply_capacity_controls` 等）はそのまま利用しつつ、戻り値を新しいデータクラスで受ける。
- 実装メモ:
  - `MappingWorkItem`（page_no, section_name, spec_slide, card, content_slide）を dataclass 化。
  - フォールバック／AI パッチ統計は `MappingAccumulator` で一元管理し、ループ外で整形する。
  - `run` 本体は `work_items` 構築 → `for item in work_items: _process_work_item(...)` → `_finalize_outputs(...)` の 3 段構成を目指す。
  - 既存のログ／メタ出力内容が変わらないことを unit/integration テストで確認する。

## 2025-11-30 DraftStructuringStep リファクタ検討メモ
- 対象: `src/pptx_generator/pipeline/draft_structuring.py` の `DraftStructuringStep.run`（約 180 行）と `_build_document`（約 220 行）。
- 現状フローと責務:
  1. **前処理**: content_approved の検証、slide alignment、テンプレート／レイアウト読込、AI リコメンダ準備。
  2. **ドキュメント構築** (`_build_document`): Draft セクション生成、AI 推薦・候補ログ生成、GenerateReady meta 用統計集計。
  3. **成果物出力**: draft/approved/log/mapping_log/generate_ready/generate_ready_meta の書き出しと DraftStore 連携。
  4. **静的モード** (`_run_static_mode`): Blueprint slot 充足チェック、GenerateReady 生成、ログ整備。
- 分割方針:
  - ランタイム状態を `DraftAccumulator`（仮）で管理し、セクション一覧・マッピングログ・AI 統計を集約。
  - `_build_work_items`（alignment 後の content/spec ペアリング）→ `_process_slide`（カード生成と候補ログ）→ `_finalize_outputs`（ファイル書き出し／DraftStore 登録）へ分割。
  - 静的モードは `_run_static_mode` 内のカード割付と GenerateReady 生成をヘルパーに切り出し、slot チェックとログ構築の分離を検討。
- 検討事項:
  - AI 推薦集計（invoked/used/simulated, models）を accumulator で一貫管理し `_build_generate_ready_meta_payload` へ渡す。
  - Slide alignment 結果や content_alignment メタの登録ロジックは run 入口付近に残し、以降の処理と責務を分離。
  - 非静的モード／静的モードで共通化できる GenerateReady 出力処理を `_write_generate_ready_outputs`（仮）として再利用。
  - 既存の JSON スキーマ・ログ構造・例外メッセージを保持し、ユニット＋ compose パイプラインテストで差分を検証する。

## 2025-11-30 DraftStructuringStep 実装メモ
- 実装内容:
  - `DraftWorkItem` / `DraftAccumulator` 導入、`_build_work_items`・`_process_work_item`・`_finalize_draft_document` を追加し、`run`／`_build_document` を三段フロー化。
  - `_build_generate_ready_meta_payload` を `_summarize_sections`・`_build_template_info`・`_build_statistics_block`・`_build_ai_recommendation_block`・`_apply_optional_generate_ready_meta` に分割。
  - 静的モードでは `_resolve_static_template_spec_path`・`_validate_static_template_spec`・`_write_static_outputs` を新設し、テンプレート解決と成果物出力の責務を整理。
- テスト: `tests/pipeline/compose/test_draft_structuring_step.py` ほか関連ケースを通過。

## 参照ログ
- 収集日: 2025-02-16
- 調査担当: Codex CLI

## 今後の検討候補（DraftStructuring 以外）
- `_build_generate_ready_meta_payload` の統計組み立てを専用ビルダーへ移し、ペイロード生成と集計ロジックを分離する。
- `_run_static_mode` のカード割付ロジックと GenerateReady 書き出しをヘルパー化し、動的モードとの共通処理を統一する。
- `MappingStep` リファクタ後のメタ統計（fallback / ai_patch）を `mapping_meta` テンプレートと照合し、不足メトリクスを洗い出す。
