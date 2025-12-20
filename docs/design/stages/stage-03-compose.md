# stage 3 Compose (HITL + 自動) 設計

対応要件: `docs/requirements/stages/stage-03-compose.md`

## 目的
- stage 2 の PrepareCard とテンプレ構造（`jobspec.json` / `layouts.jsonl`）を突合し、stage 4（PPTX 作成）が参照する `generate_ready.json` を生成する。
- HITL 承認と割当ログを `generate_ready_meta.json`・`draft_review_log.json`・`draft_mapping_log.json` に集約し、監査しやすい構造を維持する。
- 再実行や差戻しが発生した際も `<output>/draft/` 配下の成果物を固定し、CLI／自動化から運用できるようにする（既定の `--output` は `.pptx/compose`）。
- ストーリー骨子連携の補足は `docs/design/stages/stage-03-story-modeler.md` を参照。

## コンポーネント
| コンポーネント | 役割 | 技術 | 備考 |
| --- | --- | --- | --- |
| Slide ID Aligner (新規) | PrepareCard ↔ JobSpec の card/slide ID を AI で突合 | Python / slide_ai | `content_approved` の `ContentSlide.id` を補正、監査ログへ出力 |
| Draft Structuring Engine | 章構成・差戻しワークフロー | Python / dataclass | `generate_ready_meta.sections[]`・`draft_review_log.json` を管理 |
| Layout Hint Engine | レイアウト候補スコアリング | Python | Prepare の intent / chapter / Analyzer 指摘を参照 |
| GenerateReady Builder | プレースホルダ割付・フォールバック制御 | Python | `generate_ready.json`, `draft_mapping_log.json` を生成 |
| CLI | `pptx compose` / `pptx outline` | Click | compose が stage 3 全体をラップし、outline が構成再実行を担う |

## 入出力
- 入力: `jobspec.json`, `layouts.jsonl`, `prepare_card.json`（ログ／AIメタのパスは `prepare_card.json.meta.*` から参照）、（任意）`analysis_summary.json`。差戻し理由テンプレートは内蔵定義を利用する。
- 出力: `generate_ready.json`, `generate_ready_meta.json`, `draft_review_log.json`, `draft_mapping_log.json`, `fallback_report.json`。

## ワークフロー概要
1. `pptx compose` が Prepare 成果物とテンプレ構造を読み込み、通常の章構成を生成する。
2. Slide ID Aligner が `prepare_card.json` と `jobspec.json` を参照し、AI マッチングでカード ↔ スライド ID を突合。採用された ID は `content_approved` に反映し、信頼度や未確定カードをログへ記録する。
3. `CardLayoutRecommender` がカード単位でレイアウト候補を算出し、スコア内訳と共に `draft_mapping_log.json` に記録する。Analyzer 連携がある場合は重大度情報を候補に付与する。
4. HITL が CLI から章・スライド単位で承認／差戻し／付録送りを行い、操作履歴を `draft_review_log.json` に追記する。差戻し理由コードは内蔵テンプレートの定義に従って必須入力とする。
5. GenerateReady Builder が承認済みカードをテンプレ構造と突合し、カードのメッセージ／サポートポイントを `elements` として再構成しつつ、フォールバック（縮約→分割→付録送り）を適用しながら `generate_ready.json` を生成する。生成されるスライド数は PrepareCard に依存し、未割当の JobSpec スライドは出力しない。
6. `generate_ready_meta.json` を出力し、承認統計・AI 推薦採用件数・Analyzer サマリ・監査メタ情報を集約する。

## CLI
### `pptx compose`
- 主なオプション
| オプション | 説明 | 既定値 |
| --- | --- | --- |
| `<jobspec.json>` | Stage1 で抽出したジョブスペック | 必須 |
| `--prepare-cards <path>` | stage 2 の PrepareCard | `.pptx/prepare/prepare_card.json` |
| （自動） | ドラフト成果物のディレクトリ | `<output>/draft` |
| `--target-length <int>` | 目標スライド枚数 | 未指定 |
| `--structure-pattern <name>` | 章構成パターン名 | 未指定 |
| `--appendix-limit <int>` | 付録枚数の上限 | `5` |
| `--import-analysis <path>` | `analysis_summary.json` のパス | 未指定 |
| `--output, -o <dir>` | `generate_ready.json` 等の出力ディレクトリ | `.pptx/compose` |
| `--rules <path>` | 検証ルール設定ファイル | `src/pptx_generator/config/pipeline_rules.json` |
| `--show-layout-reasons` | レイアウト候補のスコア内訳を表示 | 無効 |

- ドラフト関連の追加オプション: `--target-length`, `--structure-pattern`, `--appendix-limit` など。詳細は CLI リファレンスを参照。
- 込み入った診断を確認する場合は `--show-layout-reasons`・`--preflight` を併用し、レイアウト判定根拠を CLI で即時確認できるようにする。差戻し理由コードは内蔵テンプレートを参照する。
- Analyzer 連携を再評価したい場合は `--import-analysis <path>` を指定し、`analysis_summary.json` の重大度情報を取り込む。

### `pptx outline`
- ドラフト構成のみを再実行する際に利用。`--prepare-cards` を指定すると、`prepare_card.json.meta` に記録されたログ／AIメタを自動解決する。
- 差戻し後に Draft のみ更新したいケースや UI 連携での個別更新時に利用する。

### `pptx mapping`
- stage 3 のマッピング処理だけを個別に実行し、`.pptx/gen/`（既定）配下に `generate_ready.json` などを生成するコマンド。
- `pptx compose` と同様に、Prepare 成果物は `--prepare-cards` で指定し、テンプレート／レイアウトは jobspec の `meta` から解決する。レンダリング stage（stage 4）は `pptx gen` が担当する。

## データモデル
- `chapter`: `chapter_id`, `title`, `order`, `status` など、章レーン管理に必要な情報を保持する（`chapter_template_id` などのフィールドは後方互換のため残っているが現在は未使用）。
- `slide_card`: `slide_uid`, `chapter_id`, `order`, `layout_hint`, `layout_candidates[]`, `layout_score_detail`, `analyzer_summary`, `status` など、カードごとの割付状況とスコア内訳を記録する。
- `draft_log`: `slide_uid`, `action`, `actor`, `timestamp`, `return_reason_code`, `return_reason_note`, `metadata` を持ち、HITL 操作の監査証跡を提供する。
### layout_hint スコアリング
- レイアウト候補は `uses_tag`, `content_capacity`, `diversity`, `analyzer_support` の指標でスコア化し、`draft_mapping_log.json.layout_score_detail` に理由を明示する。
- Analyzer から重大度 High の指摘がある場合は `analyzer_support` を減点し、差戻し候補として優先表示する。
- CLI では `--show-layout-reasons` 指定時に各指標の貢献度を可視化し、HITL が採用判断を行いやすくする。

### 差戻し理由テンプレート
- 差戻しコード（例: `STRUCTURE_GAP`, `ANALYZER_BLOCKER`）と推奨対応を内蔵テンプレートで管理し、ドラフト操作時の必須入力として扱う。
- 差戻し記録時は `return_reason_code` と `return_reason_note` を受け付け、コード一覧は内蔵テンプレートを参照する。
- Analyzer のブロッキングタグが存在する場合は対応する差戻しコードを優先表示し、監査ログへ `acknowledged_analyzer_risk` などのフラグを残す。

## ログ・監査
- `draft_review_log.json`: 章/スライドの承認・差戻し履歴を記録し、差戻しコードや備考を併記する。
- `draft_mapping_log.json`: レイアウト候補スコア、AI 補完、フォールバック履歴、Analyzer サマリを保持し、`layout_score_detail` でスコア内訳を確認できる。
- `fallback_report.json`: 重大フォールバックの詳細（適用戦略、対象スライド、理由）をまとめ、監査メタと紐付ける。
- `generate_ready_meta.json` には承認統計、AI 推薦採用件数などを記録し、ハッシュ情報は別途 `audit_log.json` に集約する。

## 品質ゲート
- `jobspec.json.slides[*].id` に含まれる ID はすべて `content_approved.slides[*].id` に存在することを必須とし、不一致が 1 件でも見つかった場合は `DraftStructuringError` を送出して stage 3 を即時停止する。エラーメッセージには欠損 ID 一覧を含め、CLI 側では exit code 6 として扱う。
- Slide ID Aligner が `content_approved` を補正した後も未解決の ID が残るケースを前提とし、品質ゲートに到達する前に INFO ログで検出状況を通知する。
- 例外発生時は `<output>/draft/` 配下へ中間成果物を出力せず、HITL は `prepare_card.json` / `jobspec.json` を突合して ID 設定ミスを修正した上で再実行する。
- 差戻し理由コード未指定や未承認スライドが残った状態で章承認コマンドを実行した場合は `422 Unprocessable Entity` を返し、CLI は再入力を促す。
- `analysis_summary.json` に存在しないスライド ID が Import された場合は `400 Bad Request` とし、不一致一覧を含む詳細メッセージを返却する。
- 静的テンプレ用外部フック: 静的モードで `external/<template_id>/hooks.json` が定義されている場合、`pptx compose` / `pptx mapping` / `pptx gen` 各ステージでフックを呼び出せる。環境変数例: `PPTX_STAGE=compose`, `PPTX_TEMPLATE_ID`, `PPTX_SPEC_PATH`, `PPTX_OUTPUT_DIR`, `PPTX_DRAFT_OUTPUT`, `PPTX_RULES_PATH`, `PPTX_PREPARE_CARDS_PATH`, `PPTX_GENERATE_READY_PATH`。スライド別フックでは `PPTX_SLIDE_KEY=01_system-layout`, `PPTX_SLIDE_ID`, `PPTX_SLIDE_LAYOUT`, `PPTX_SLIDE_PAGE_NO` を提供し、`continue_default=false` 指定により既存処理をスキップして外部スクリプトで `generate_ready.json` などを生成できる。

## Analyzer 連携
- `analysis_summary.json` を `--analysis-summary` で読み込み、重大度 High の指摘があるカードには `analyzer_context` を付与する。
- Analyzer 指摘件数が閾値を超える場合は候補スコアを減点し、差戻しを優先表示する。
- CLI `--show-analyzer` オプション（検討中）で章/スライド単位の重大度サマリを一覧表示し、HITL が優先対応すべき箇所を把握できるようにする。
- 静的テンプレ用外部フック: 静的モードで `external/<template_id>/hooks.json` が存在する場合、`pptx compose` / `pptx mapping` / `pptx gen` はステージ前後で外部スクリプトを呼び出す。共通環境変数例: `PPTX_STAGE=compose`, `PPTX_TEMPLATE_ID`, `PPTX_SPEC_PATH`, `PPTX_OUTPUT_DIR`, `PPTX_DRAFT_OUTPUT`, `PPTX_RULES_PATH`, `PPTX_PREPARE_CARDS_PATH`。スライド別フックは、`generate_ready.json` に基づいて `PPTX_SLIDE_KEY=01_system-layout`, `PPTX_SLIDE_ID`, `PPTX_SLIDE_LAYOUT`, `PPTX_SLIDE_PAGE_NO` を受け取る。`continue_default=false` 指定により既存の内部処理をスキップし、外部スクリプトで `generate_ready.json` 等を生成することも可能。

## エラーハンドリング
- 承認済み章に対する構成変更は `409 Conflict` とし、事前に差戻し操作を挟むことを要求する。
- layout_hint 未選択で承認操作を行った場合は `400 Bad Request` を返し、必要な入力を CLI に表示する。
- Analyzer ブロッカーを無視して承認した場合は `draft_review_log` に `acknowledged_analyzer_risk=true` を記録して監査対象とする。

## 監視とメトリクス
- Prometheus で `draft_return_reason_count{code=...}`, `draft_analyzer_blockers_total` などのメトリクスを収集し、HITL 負荷や品質リスクを可視化する。
- 差戻し回数などの指標をダッシュボード化し、構成の安定度を継続的にモニタリングする。
- レイアウト候補スコアの偏りや Analyzer 重大度の未処理件数をアラート条件として設定する。

## 未解決事項
- 章テンプレ適合率の計算ロジックと Stage4 の `generate_ready_meta.template` との整合。
- レイアウト候補スコアの ML 化と継続学習。
- `draft_mapping_log.json` のダイジェスト表示（CLI/監視ダッシュボード）実装。
- Analyzer 指摘と差戻し理由コードの自動マッピング。
- layout_hint 候補計算で利用する差戻しテンプレートや Analyzer 指標の閾値管理。
- 差戻しテンプレのライフサイクル管理と翻訳対応。
